import re
from json import dumps as json_dumps

from django.db.models import Count
from kombu.exceptions import OperationalError

from django.utils.translation import gettext_lazy as _, gettext
from django.http.response import StreamingHttpResponse
from guardian.shortcuts import get_objects_for_user
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework import status
from easysnmp import EasySNMPTimeoutError
from django_filters.rest_framework import DjangoFilterBackend

from customers.models import Customer
from messenger.tasks import multicast_viber_notify
from devices.switch_config import (
    DeviceImplementationError, DeviceConsoleError,
    ExpectValidationError, macbin2str, DeviceConnectionError,
    BaseSwitchInterface, BasePONInterface, BasePortInterface)
from djing2 import IP_ADDR_REGEX
from djing2.lib import ProcessLocked, safe_int, ws_connector, RuTimedelta
from djing2.viewsets import DjingModelViewSet, DjingListAPIView
from devices.models import Device, Port, PortVlanMemberModel
from devices import serializers as dev_serializers
from devices.tasks import onu_register
from groupapp.models import Group
from profiles.models import UserProfile


def catch_dev_manager_err(fn):
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except DeviceImplementationError as err:
            return Response(str(err), status=status.HTTP_501_NOT_IMPLEMENTED)
        except ExpectValidationError as err:
            return Response(str(err))
        except (ConnectionResetError, ConnectionRefusedError, OSError, DeviceConnectionError, EasySNMPTimeoutError) as err:
            return Response(str(err), status=status.HTTP_503_SERVICE_UNAVAILABLE)

    # Hack for decorator @action
    wrapper.__name__ = fn.__name__
    return wrapper


class DeviceModelViewSet(DjingModelViewSet):
    queryset = Device.objects.all()
    serializer_class = dev_serializers.DeviceModelSerializer
    filterset_fields = ('group', 'dev_type', 'status', 'is_noticeable')
    filter_backends = (SearchFilter, DjangoFilterBackend)
    search_fields = ('comment', 'ip_address', 'mac_addr')

    def destroy(self, *args, **kwargs):
        r = super().destroy(*args, **kwargs)
        onu_register.delay(
            tuple(dev.pk for dev in Device.objects.exclude(group=None).only('pk').iterator())
        )
        return r

    def create(self, *args, **kwargs):
        r = super().create(*args, **kwargs)
        onu_register.delay(
            tuple(dev.pk for dev in Device.objects.exclude(group=None).only('pk').iterator())
        )
        return r

    @action(detail=True)
    @catch_dev_manager_err
    def scan_units_unregistered(self, request, pk=None):
        device = self.get_object()
        manager = device.get_manager_object_olt()
        if hasattr(manager, 'get_fibers'):
            unregistered = []
            for fb in manager.get_fibers():
                for unr in manager.get_units_unregistered(int(fb.get('fb_id'))):
                    unregistered.append(unr)
            return Response(unregistered)
        return DeviceImplementationError('Manager has not get_fibers attribute')

    @action(detail=True)
    @catch_dev_manager_err
    def scan_onu_list(self, request, pk=None):
        device = self.get_object()
        manager = device.get_manager_object()
        if not issubclass(manager.__class__, BasePONInterface):
            raise DeviceImplementationError('Expected BasePONInterface subclass')

        def chunk_cook(chunk: dict) -> bytes:
            chunk_json = json_dumps(chunk, ensure_ascii=False)
            chunk_json = '%s\n' % chunk_json
            format_string = '{:%ds}' % chunk_max_len
            dat = format_string.format(chunk_json)
            return dat.encode()[:chunk_max_len]

        try:
            onu_list = manager.scan_onu_list()
            item_size = next(onu_list)
            chunk_max_len = next(onu_list)
            r = StreamingHttpResponse(streaming_content=(chunk_cook({
                'number': p.num,
                'name': p.name,
                'status': p.status,
                'mac_addr': macbin2str(p.mac),
                'signal': p.signal,
                'uptime': str(RuTimedelta(seconds=p.uptime / 100)) if p.uptime else None
            }) for p in onu_list))
            r['Content-Length'] = item_size * chunk_max_len
            r['Cache-Control'] = 'no-store'
            r['Content-Type'] = 'application/octet-stream'
            return r
        except StopIteration:
            pass
        return Response('No all fetched')

    @action(detail=True)
    @catch_dev_manager_err
    def scan_ports(self, request, pk=None):
        device = self.get_object()
        manager = device.get_manager_object()
        if not issubclass(manager.__class__, BaseSwitchInterface):
            raise DeviceImplementationError('Expected BaseSwitchInterface subclass')
        ports = manager.get_ports()
        db_ports = Port.objects.filter(device__id=pk).annotate(user_count=Count('customer'))

        def join_with_db(p: BasePortInterface):
            r = p.to_dict()
            ps = [dbp for dbp in db_ports if p.num == dbp.num]
            if len(ps) > 0:
                db_port = dev_serializers.PortModelSerializer(ps[0]).data
                del db_port['num']
                r.update({
                    'db': db_port
                })
            return r

        return Response(data=(join_with_db(p) for p in ports))

    @action(detail=True)
    @catch_dev_manager_err
    def scan_details(self, request, pk=None):
        device = self.get_object()
        manager = device.get_manager_object()
        data = manager.get_details()
        return Response(data)

    @action(detail=True)
    @catch_dev_manager_err
    def scan_olt_fibers(self, request, pk=None):
        device = self.get_object()
        manager = device.get_manager_object_olt()
        if hasattr(manager, 'get_fibers'):
            fb = manager.get_fibers()
            return Response(fb)
        else:
            return Response({'Error': {
                'text': 'Manager has not get_fibers attribute'
            }})

    @action(detail=True, methods=('put',))
    @catch_dev_manager_err
    def send_reboot(self, request, pk=None):
        device = self.get_object()
        manager = device.get_manager_object()
        manager.reboot(save_before_reboot=False)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True)
    @catch_dev_manager_err
    def fix_onu(self, request, pk=None):
        onu = self.get_object()
        fix_status, text = onu.fix_onu()
        if fix_status:
            return Response(text, status.HTTP_200_OK)
        return Response(text, status.HTTP_404_NOT_FOUND)

    @action(detail=True)
    @catch_dev_manager_err
    def register_device(self, request, pk=None):
        device = self.get_object()
        http_status = status.HTTP_200_OK
        res_status = 1  # 'ok'
        try:
            device.register_device()
        except DeviceConsoleError as e:
            text = str(e)
            res_status = 2
        except (ConnectionRefusedError, ExpectValidationError) as e:
            text = e
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
            res_status = 2
        except ProcessLocked:
            text = gettext('Process locked by another process')
            res_status = 2
        else:
            text = gettext('ok')
        return Response({'text': text, 'status': res_status}, status=http_status)

    @action(detail=True)
    @catch_dev_manager_err
    def remove_from_olt(self, request, pk=None):
        device = self.get_object()
        if device.remove_from_olt():
            return Response(_('Deleted'))
        return Response(_('Failed'))

    @action(detail=True)
    @catch_dev_manager_err
    def monitoring_event(self, request, pk=None):
        try:
            dev_ip = request.query_params.get('dev_ip')
            dev_status = safe_int(request.query_params.get('status'))
            if not dev_ip:
                return Response({'text': 'ip does not passed'})
            if not re.match(IP_ADDR_REGEX, dev_ip):
                return Response({'text': 'ip address %s is not valid' % dev_ip})

            device_down = self.get_queryset().filter(
                ip_address=dev_ip
            ).defer(
                'extra_data'
            ).first()
            if device_down is None:
                return Response({
                    'text': 'Devices with ip %s does not exist' % dev_ip
                })

            status_map = {
                'UP': 1,
                'UNREACHABLE': 2,
                'DOWN': 3
            }
            status_text_map = {
                'UP': 'Device %(device_name)s is up',
                'UNREACHABLE': 'Device %(device_name)s is unreachable',
                'DOWN': 'Device %(device_name)s is down'
            }
            device_down.status = status_map.get(dev_status, 0)

            device_down.save(update_fields=('status',))

            if not device_down.is_noticeable:
                return {
                    'text': 'Notification for %s is unnecessary' %
                            device_down.ip_address or device_down.comment
                }

            if not device_down.group:
                return Response({
                    'text': 'Device has not have a group'
                })

            recipients = UserProfile.objects.get_profiles_by_group(
                group_id=device_down.group.pk
            ).filter(flags=UserProfile.flags.notify_mon)
            user_ids = tuple(recipient.pk for recipient in recipients.only('pk').iterator())

            notify_text = status_text_map.get(
                dev_status,
                default='Device %(device_name)s getting undefined status code'
            )
            text = gettext(notify_text) % {
                'device_name': "%s(%s) %s" % (
                    device_down.ip_address or '',
                    device_down.mac_addr,
                    device_down.comment
                )
            }
            multicast_viber_notify.delay(
                messenger_id=None,
                account_id_list=user_ids,
                message_text=text
            )
            ws_connector.send_data({
                'type': 'monitoring_event',
                'recipients': user_ids,
                'text': text
            })
            return Response({'text': 'notification successfully sent'})
        except (ValueError, OperationalError) as e:
            return Response({
                'text': str(e)
            })

    @action(detail=True)
    @catch_dev_manager_err
    def scan_mac_address_vlan(self, request, pk=None):
        dev = self.get_object()
        vid = safe_int(request.query_params.get('vid'))
        if vid == 0:
            return Response('Valid vid required', status=status.HTTP_400_BAD_REQUEST)
        macs = dev.dev_read_mac_address_vlan(
            vid=vid
        )
        return Response([m._asdict() for m in macs])

    @action(detail=True)
    @catch_dev_manager_err
    def scan_all_vlan_list(self, request, pk=None):
        dev = self.get_object()
        vlans = dev.dev_get_all_vlan_list()
        res = (i._asdict() for i in vlans)
        return Response(res)


class DeviceWithoutGroupListAPIView(DjingListAPIView):
    queryset = Device.objects.filter(group=None)
    serializer_class = dev_serializers.DeviceWithoutGroupModelSerializer


class PortModelViewSet(DjingModelViewSet):
    queryset = Port.objects.annotate(user_count=Count('customer'))
    serializer_class = dev_serializers.PortModelSerializer
    filterset_fields = ('device', 'num')

    @action(detail=True)
    @catch_dev_manager_err
    def toggle_port(self, request, pk=None):
        port_state = request.query_params.get('state')
        port = self.get_object()
        port_num = int(port.num)
        manager = port.device.get_manager_object_switch()
        if port_state == 'up':
            manager.port_enable(port_num=port_num)
        elif port_state == 'down':
            manager.port_disable(port_num=port_num)
        else:
            return Response(_('Parameter port_state is bad'), status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True)
    @catch_dev_manager_err
    def get_subscriber_on_port(self, request, pk=None):
        dev_id = request.query_params.get('device_id')
        # port = self.get_object()
        customers = Customer.objects.filter(device_id=dev_id, dev_port_id=pk)
        if not customers.exists():
            raise NotFound(gettext('Subscribers on port does not exist'))
        if customers.count() > 1:
            return Response([c for c in customers])
        return Response(self.serializer_class(instance=customers.first()))

    @action(detail=True)
    @catch_dev_manager_err
    def scan_mac_address_port(self, request, pk=None):
        port = self.get_object()
        dev = port.device
        if dev is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        macs = dev.dev_switch_get_mac_address_port(
            device_port_num=port.num
        )
        return Response([m._asdict() for m in macs])


class PortVlanMemberModelViewSet(DjingModelViewSet):
    queryset = PortVlanMemberModel.objects.all()
    serializer_class = dev_serializers.PortVlanMemberModelSerializer
    filterset_fields = ('vlanif', 'port')


class DeviceGroupsList(DjingListAPIView):
    serializer_class = dev_serializers.DeviceGroupsModelSerializer
    filter_backends = (OrderingFilter,)
    ordering_fields = ('title', 'code')

    def get_queryset(self):
        groups = get_objects_for_user(
            self.request.user,
            'groupapp.view_group', klass=Group,
            accept_global_perms=False
        ).annotate(device_count=Count('device'))
        return groups
