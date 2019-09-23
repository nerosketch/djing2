import re

from kombu.exceptions import OperationalError
from json import dumps as json_dumps

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _, gettext
from django.http.response import StreamingHttpResponse
from guardian.shortcuts import get_objects_for_user
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework import status
from easysnmp import EasySNMPTimeoutError
from django_filters.rest_framework import DjangoFilterBackend

from customers.models import Customer
from messenger.tasks import multicast_viber_notify
from devices.base_intr import DeviceImplementationError
from djing2 import IP_ADDR_REGEX
from djing2.lib import ProcessLocked, safe_int
from djing2.viewsets import DjingModelViewSet, DjingListAPIView
from devices.models import Device, Port
from devices import serializers as dev_serializers
from devices.tasks import onu_register
from groupapp.models import Group


UserProfile = get_user_model()


def catch_dev_manager_err(fn):
    def wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except DeviceImplementationError as err:
            return Response({'Error': {
                'text': '%s' % err
            }}, status=status.HTTP_501_NOT_IMPLEMENTED)
        except (ConnectionResetError, EasySNMPTimeoutError) as err:
            return Response({'Error': {
                'text': '%s' % err
            }}, status=status.HTTP_408_REQUEST_TIMEOUT)

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
    def scan_units_unregistered(self, request, pk=None):
        device = self.get_object()
        manager = device.get_manager_object()
        if hasattr(manager, 'get_fibers'):
            unregistered = []
            for fb in manager.get_fibers():
                for unr in manager.get_units_unregistered(int(fb.get('fb_id'))):
                    unregistered.append(unr)

            # print(unregistered, list(unregistered))
            return Response(unregistered)
        return Response({'Error': {
            'text': 'Manager has not get_fibers attribute'
        }})

    @action(detail=True)
    @catch_dev_manager_err
    def scan_ports(self, request, pk=None):
        device = self.get_object()
        manager = device.get_manager_object()
        # TODO: get max len from manager,
        # implement get_ports for other devices
        chunk_max_len = 200

        def chunk_cook(chunk) -> bytes:
            chunk_json = json_dumps(chunk, ensure_ascii=False)
            chunk_json = '%s\n' % chunk_json
            format_string = '{:%ds}' % chunk_max_len
            dat = format_string.format(chunk_json)
            return dat.encode()[:chunk_max_len]
        try:
            ports = manager.get_ports()
            items_count = next(ports)
            r = StreamingHttpResponse(streaming_content=(chunk_cook(p.to_dict()) for p in ports))
            r['Content-Length'] = items_count * chunk_max_len
            r['Cache-Control'] = 'no-store'
            r['Content-Type'] = 'application/octet-stream'
            return r
        except StopIteration:
            pass
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True)
    @catch_dev_manager_err
    def scan_details(self, request, pk=None):
        device = self.get_object()
        manager = device.get_manager_object()
        data = manager.get_details()
        return Response(data)

    @action(detail=True)
    @catch_dev_manager_err
    def scan_fibers(self, request, pk=None):
        device = self.get_object()
        manager = device.get_manager_object()
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
    def toggle_port(self, request, pk=None):
        device = self.get_object()
        manager = device.get_manager_object()
        port_id = request.query_params.get('port_id')
        port_state = request.query_params.get('state')
        if not port_id or not port_id.isdigit():
            return Response(_('Parameter port_id is bad'), status=status.HTTP_400_BAD_REQUEST)
        ports = tuple(manager.get_ports())
        port_id = int(port_id)
        if port_state == 'up':
            ports[port_id - 1].enable()
        elif port_state == 'down':
            ports[port_id - 1].disable()
        else:
            return Response(_('Parameter port_state is bad'), status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True)
    @catch_dev_manager_err
    def fix_onu(self, request, pk=None):
        onu = self.get_object()
        parent = onu.parent_dev
        if parent is not None:
            manager = onu.get_manager_object()
            mac = onu.mac_addr
            ports = manager.get_list_keyval('.1.3.6.1.4.1.3320.101.10.1.1.3')
            text = _('Device with mac address %(mac)s does not exist') % mac
            http_status = status.HTTP_404_NOT_FOUND
            for srcmac, snmpnum in ports:
                # convert bytes mac address to str presentation mac address
                real_mac = ':'.join('%x' % ord(i) for i in srcmac)
                if mac == real_mac:
                    onu.snmp_extra = str(snmpnum)
                    onu.save(update_fields=('snmp_extra',))
                    text = _('Fixed')
                    http_status = status.HTTP_200_OK
        else:
            text = _('Parent device not found')
            http_status = status.HTTP_404_NOT_FOUND
        return Response(text, http_status)

    @action(detail=True)
    @catch_dev_manager_err
    def register_device(self, request, pk=None):
        from devices import expect_scripts
        device = self.get_object()
        http_status = status.HTTP_200_OK
        try:
            device.register_device()
        except expect_scripts.OnuZteRegisterError:
            text = gettext('Unregistered onu not found')
        except expect_scripts.ZteOltLoginFailed:
            text = gettext('Wrong login or password for telnet access')
        except (
                ConnectionRefusedError, expect_scripts.ZteOltConsoleError,
                expect_scripts.ExpectValidationError, expect_scripts.ZTEFiberIsFull
        ) as e:
            text = e
            http_status = status.HTTP_503_SERVICE_UNAVAILABLE
        except ProcessLocked:
            text = gettext('Process locked by another process')
        else:
            text = gettext('ok')
        return Response(text, status=http_status)

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
            return Response({'text': 'notification successfully sent'})
        except (ValueError, OperationalError) as e:
            return Response({
                'text': str(e)
            })


class DeviceWithoutGroupListAPIView(DjingListAPIView):
    queryset = Device.objects.filter(group=None)
    serializer_class = dev_serializers.DeviceWithoutGroupModelSerializer


class PortModelViewSet(DjingModelViewSet):
    queryset = Port.objects.all()
    serializer_class = dev_serializers.PortModelSerializer
    filterset_fields = ('device', 'num')

    @action(detail=False)
    @catch_dev_manager_err
    def extended(self, request):
        self.serializer_class = dev_serializers.PortModelSerializerExtended
        return super().list(request)

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


class DeviceGroupsList(DjingListAPIView):
    serializer_class = dev_serializers.DeviceGroupsModelSerializer

    def get_queryset(self):
        groups = get_objects_for_user(
            self.request.user,
            'groupapp.view_group', klass=Group,
            accept_global_perms=False
        )
        return groups
