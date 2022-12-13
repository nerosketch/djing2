import re
from functools import wraps
from json import dumps as json_dumps
from dataclasses import asdict
from typing import Optional, Union

from django.contrib.sites.models import Site
from django.db.models import Count, QuerySet
from django.http.response import StreamingHttpResponse
from django.utils.translation import gettext_lazy as _, gettext
from django_filters.rest_framework import DjangoFilterBackend
from djing2.lib.fastapi.general_filter import general_filter_queryset
from djing2.lib.fastapi.pagination import paginate_qs_path_decorator
from djing2.lib.fastapi.perms import permission_check_dependency
from djing2.lib.fastapi.sites_depend import sites_dependency
from djing2.lib.fastapi.types import IListResponse, Pagination
from djing2.lib.fastapi.utils import get_object_or_404
from easysnmp.exceptions import EasySNMPTimeoutError, EasySNMPError
from guardian.shortcuts import get_objects_for_user
from starlette import status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response as OldResponse
from rest_framework.utils.encoders import JSONEncoder

from fastapi import APIRouter, Request, Depends, Response, Query, Path, HTTPException

from djing2.lib.fastapi.auth import is_admin_auth_dependency, TOKEN_RESULT_TYPE
from djing2.lib.filters import CustomSearchFilter
from devices import serializers as dev_serializers
from devices.device_config.pon.pon_device_strategy import PonOLTDeviceStrategyContext, FiberDataClass
from devices.device_config.switch.switch_device_strategy import SwitchDeviceStrategyContext
from devices.models import Device, Port, PortVlanMemberModel, DeviceModelQuerySet, DeviceStatusEnum
from devices.device_config.base import (
    DeviceImplementationError,
    DeviceConnectionError,
    UnsupportedReadingVlan, DeviceTimeoutError,
)
from devices.device_config.expect_util import ExpectValidationError
from djing2 import IP_ADDR_REGEX
from djing2.lib import ProcessLocked, safe_int, RuTimedelta
from djing2.lib.custom_signals import notification_signal
from djing2.lib.filters import CustomObjectPermissionsFilter
from djing2.viewsets import DjingModelViewSet, DjingListAPIView
from groupapp.models import Group
from profiles.models import UserProfile, UserProfileLogActionType
from . import schemas


router = APIRouter(
    prefix='/devices',
    tags=['Devices'],
    dependencies=[Depends(is_admin_auth_dependency)]
)


def catch_dev_manager_err(fn):
    @wraps(fn)
    def _wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except (DeviceImplementationError, ExpectValidationError) as err:
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail={"text": str(err), "status": 2}
            )
        except EasySNMPTimeoutError as err:
            raise DeviceTimeoutError() from err
        except (
            ConnectionResetError,
            ConnectionRefusedError,
            OSError,
            DeviceConnectionError,
            EasySNMPError,
        ) as err:
            raise HTTPException(
                detail=str(err),
                status_code=452
            )
        except SystemError as err:
            raise HTTPException(
                detail=str(err),
                status_code=453
            )

    return _wrapper


def filter_query_set_dependency(
    auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
    house: Optional[int] = None,
    street: Optional[int] = None,
    address: Optional[int] = None
) -> QuerySet[Device]:
    curr_user, token = auth
    qs = Device.objects.select_related("parent_dev").order_by('comment')
    if curr_user.is_superuser:
        return qs
    grps = get_objects_for_user(user=curr_user, perms="groupapp.view_group", klass=Group).order_by("title")
    qs = qs.filter(group__in=grps)

    if house and house > 0:
        return qs.filter_devices_by_addr(
            addr_id=house,
        )
    elif street and street > 0:
        return qs.filter_devices_by_addr(
            addr_id=street,
        )
    if address and address > 0:
        return qs.filter_devices_by_addr(
            addr_id=address,
        )
    return qs


@router.get(
    '/pon/',
    response_model=IListResponse[schemas.DevicePONModelSchema],
    response_model_exclude_none=True
)
@paginate_qs_path_decorator(
    schema=schemas.DevicePONModelSchema,
    db_model=Device
)
def get_pon_devices(
    request: Request,
    group: Optional[int] = Query(default=None, gt=0),
    dev_type: Optional[int] = Query(default=None, gt=0),
    dev_status: Optional[int] = Query(default=None, gt=0, alias='status'),
    is_noticeable: Optional[int] = Query(default=None, gt=0),
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='devices.view_device'
    )),
    curr_site: Site = Depends(sites_dependency),
    pagination: Pagination = Depends(),
    dev_initial_qs: QuerySet[Device] = Depends(filter_query_set_dependency)
):
    qs = general_filter_queryset(
        qs_or_model=dev_initial_qs,
        curr_site=curr_site,
        curr_user=curr_user,
        perm_codename='devices.view_device',
    )
    if isinstance(group, int):
        qs = qs.filter(group_id=group)
    if isinstance(dev_type, int):
        qs = qs.filter(dev_type=dev_type)
    if isinstance(dev_status, int):
        qs = qs.filter(status=dev_status)
    if isinstance(is_noticeable, int):
        qs = qs.filter(is_noticeable=is_noticeable)

    return qs


@router.get('/pon/{device_id}/scan_units_unregistered/',
            response_model=list)
def scan_units_unregistered(
    device_id: int = Path(gt=0),
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='devices.view_device'
    )),
    curr_site: Site = Depends(sites_dependency),
):
    qs = general_filter_queryset(
        qs_or_model=Device,
        curr_site=curr_site,
        curr_user=curr_user,
        perm_codename='devices.view_device',
    )
    device = get_object_or_404(qs, pk=device_id)
    manager = device.get_pon_olt_device_manager()
    if hasattr(manager, "get_fibers"):
        unregistered = []
        for fb in manager.get_fibers():
            for unr in manager.get_units_unregistered(fb):
                unregistered.append(unr)
        return unregistered
    raise DeviceImplementationError(
        detail="Manager has not get_fibers attribute"
    )


@router.get(
    '/pon/{device_id}/scan_olt_fibers/',
)
def scan_olt_fibers(
    device_id: int = Path(gt=0),
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='devices.view_device'
    )),
    curr_site: Site = Depends(sites_dependency),
):
    qs = general_filter_queryset(
        qs_or_model=Device,
        curr_site=curr_site,
        curr_user=curr_user,
        perm_codename='devices.view_device',
    )
    device = get_object_or_404(qs, pk=device_id)
    manager = device.get_pon_olt_device_manager()
    if hasattr(manager, "get_fibers"):
        fb = manager.get_fibers()
        return tuple(fb)
    return Response({"Error": {"text": "Manager has not get_fibers attribute"}})


class DevicePONViewSet(DjingModelViewSet):
    # queryset = Device.objects.select_related("parent_dev").order_by('comment')
    # serializer_class = dev_serializers.DevicePONModelSerializer
    # filterset_fields = ("group", "dev_type", "status", "is_noticeable")
    # filter_backends = [CustomObjectPermissionsFilter, DjangoFilterBackend, CustomSearchFilter]
    # search_fields = ("comment", "ip_address", "mac_addr")
    # ordering_fields = ("ip_address", "mac_addr", "comment", "dev_type")

    @action(detail=True)
    @catch_dev_manager_err
    def scan_onu_list(self, request, pk=None):
        device = self.get_object()
        manager = device.get_pon_olt_device_manager()
        if not isinstance(manager, PonOLTDeviceStrategyContext):
            raise DeviceImplementationError("Expected PonOLTDeviceStrategyContext instance")

        def chunk_cook(chunk: dict) -> bytes:
            chunk_json = json_dumps(chunk, ensure_ascii=False, cls=JSONEncoder)
            chunk_json = "%s\n" % chunk_json
            format_string = "{:%ds}" % chunk_max_len
            dat = format_string.format(chunk_json)
            return dat.encode()[:chunk_max_len]

        try:
            onu_list = manager.scan_onu_list()
            item_size = next(onu_list)
            chunk_max_len = next(onu_list)
            r = StreamingHttpResponse(
                streaming_content=(
                    chunk_cook(
                        {
                            "number": p.num,
                            "title": p.name,
                            "status": p.status,
                            "mac_addr": p.mac,
                            "signal": p.signal,
                            "uptime": str(RuTimedelta(seconds=p.uptime / 100)) if p.uptime else None,
                            "fiberid": p.fiberid,
                        }
                    )
                    for p in onu_list
                )
            )
            r["Content-Length"] = item_size * chunk_max_len
            r["Cache-Control"] = "no-store"
            r["Content-Type"] = "application/octet-stream"
            return r
        except StopIteration:
            pass
        return OldResponse("No all fetched")

    @action(detail=True, url_path=r"scan_onu_on_fiber/(?P<fiber_num>\d{8,12})")
    @catch_dev_manager_err
    def scan_onu_on_fiber(self, request, fiber_num=0, pk=None):
        if not str(fiber_num).isdigit() or safe_int(fiber_num) < 1:
            return OldResponse('"fiber_num" number param required', status=status.HTTP_400_BAD_REQUEST)
        fiber_num = safe_int(fiber_num)
        device = self.get_object()
        manager = device.get_pon_olt_device_manager()
        if hasattr(manager, "get_ports_on_fiber"):
            try:
                onu_list = tuple(manager.get_ports_on_fiber(fiber_num=fiber_num))
                return OldResponse(onu_list)
            except ProcessLocked:
                return OldResponse(_("Process locked by another process"), status=452)
        else:
            return OldResponse({"Error": {"text": 'Manager has not "get_ports_on_fiber" attribute'}})

    @action(detail=True)
    @catch_dev_manager_err
    def fix_onu(self, request, pk=None):
        self.check_permission_code(request, "devices.can_fix_onu")
        onu = self.get_object()
        fix_status, text = onu.fix_onu()
        onu_serializer = self.get_serializer(onu)
        return OldResponse({"text": text, "status": 1 if fix_status else 2, "device": onu_serializer.data})

    @action(detail=True, methods=["post"])
    @catch_dev_manager_err
    def apply_device_onu_config_template(self, request, pk=None):
        self.check_permission_code(request, "devices.can_apply_onu_config")

        # mng = device.get_manager_object_onu()
        # if not isinstance(mng, BasePON_ONU_Interface):
        #     return OldResponse("device must be PON ONU type", status=status.HTTP_400_BAD_REQUEST)

        # TODO: Describe this as TypedDict from python3.8
        # apply config
        # example = {
        #     'configTypeCode': 'zte_f660_bridge',
        #     'vlanConfig': [
        #         {
        #             'port': 1,
        #             'vids': [
        #                 {'vid': 151, 'native': True}
        #             ]
        #         },
        #         {
        #             'port': 2,
        #             'vids': [
        #                 {'vid': 263, 'native': False},
        #                 {'vid': 264, 'native': False},
        #                 {'vid': 265, 'native': False},
        #             ]
        #         }
        #     ]
        # }
        device_config_serializer = dev_serializers.DeviceOnuConfigTemplate(data=request.data)
        device_config_serializer.is_valid(raise_exception=True)

        device = self.get_object()
        res = device.apply_onu_config(config=device_config_serializer.data)
        return OldResponse(res)

    @action(detail=True, methods=['get'])
    @catch_dev_manager_err
    def remove_from_olt(self, request, pk=None):
        self.check_permission_code(request, "devices.can_remove_from_olt")
        device = self.get_object()
        args = request.query_params
        if device.remove_from_olt(**args):
            return OldResponse({"text": _("Deleted"), "status": 1})
        return OldResponse({"text": _("Failed"), "status": 2})

    @action(detail=True)
    @catch_dev_manager_err
    def scan_pon_details(self, request, pk=None):
        device = self.get_object()
        pon_manager = device.get_pon_onu_device_manager()
        data = pon_manager.get_details()
        return OldResponse(data)

    @action(detail=True)
    def get_onu_config_options(self, request, pk=None):
        dev = self.get_object()
        config_types = dev.get_config_types()
        config_choices = (i.to_dict() for i in config_types if i)
        # klass = dev.get_manager_klass()

        res = {
            # 'port_num': klass.ports_len,
            "config_choices": config_choices,
            # 'accept_vlan': True or not True  # or not to be :)
        }

        return OldResponse(res)

    @action(detail=True)
    @catch_dev_manager_err
    def read_onu_vlan_info(self, request, pk=None):
        try:
            dev = self.get_object()
            if dev.is_onu_registered:
                vlans = tuple(dev.read_onu_vlan_info())
            else:
                vlans = dev.default_vlan_info()
            return OldResponse(vlans)
        except UnsupportedReadingVlan:
            # Vlan config unsupported
            return OldResponse(())


class DeviceModelViewSet(DjingModelViewSet):
    queryset = Device.objects.select_related("parent_dev").order_by('comment')
    serializer_class = dev_serializers.DeviceModelSerializer
    filterset_fields = ("group", "dev_type", "status", "is_noticeable", "address")
    filter_backends = (CustomObjectPermissionsFilter, CustomSearchFilter, DjangoFilterBackend)
    search_fields = ("comment", "ip_address", "mac_addr")
    ordering_fields = ("ip_address", "mac_addr", "comment", "dev_type")

    def perform_create(self, serializer, *args, **kwargs):
        device_instance = super().perform_create(serializer=serializer, sites=[self.request.site])
        if device_instance is not None:
            self.request.user.log(
                do_type=UserProfileLogActionType.CREATE_DEVICE,
                additional_text='ip %s, mac: %s, "%s"'
                % (device_instance.ip_address, device_instance.mac_addr, device_instance.comment),
            )
        return device_instance

    def perform_destroy(self, instance):
        # log about it
        self.request.user.log(
            do_type=UserProfileLogActionType.DELETE_DEVICE,
            additional_text='ip %s, mac: %s, "%s"'
            % (instance.ip_address or "-", instance.mac_addr or "-", instance.comment or "-"),
        )
        return super().perform_destroy(instance)

    @action(detail=True)
    @catch_dev_manager_err
    def scan_ports(self, request, pk=None):
        device = self.get_object()
        manager = device.get_switch_device_manager()
        if not isinstance(manager, SwitchDeviceStrategyContext):
            raise DeviceImplementationError("Expected SwitchDeviceStrategyContext instance")
        try:
            ports = [p.as_dict() for p in manager.get_ports()]
            return OldResponse({"text": '', "status": 1, "ports": ports})
        except StopIteration:
            return OldResponse({"text": _("Device port count error"), "status": 2})

    @action(detail=True, methods=["put"])
    @catch_dev_manager_err
    def send_reboot(self, request, pk=None):
        device = self.get_object()
        manager = device.get_switch_device_manager()
        manager.reboot(save_before_reboot=False)
        return OldResponse(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"])
    @catch_dev_manager_err
    def zbx_monitoring_event(self, request):
        dat = request.data
        dev_ip = dat.get("dev_ip")
        dev_status = dat.get("status")
        message = dat.get('message')
        dev_status = safe_int(dev_status)
        if not dev_ip:
            return OldResponse(
                {"text": "ip does not passed"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not re.match(IP_ADDR_REGEX, dev_ip):
            return OldResponse(
                {"text": "ip address %s is not valid" % dev_ip},
                status=status.HTTP_400_BAD_REQUEST
            )

        device = self.get_queryset().filter(ip_address=dev_ip).defer("extra_data").first()
        if device is None:
            return OldResponse(
                {"text": "Devices with ip %s does not exist" % dev_ip},
                status=status.HTTP_404_NOT_FOUND
            )

        status_map = {
            0: DeviceStatusEnum.NETWORK_STATE_UP.value,
            1: DeviceStatusEnum.NETWORK_STATE_DOWN.value,
        }
        status_text_map = {
            0: "Device %(device_name)s is ok",
            1: "Device %(device_name)s has problem",
        }
        device.status = status_map.get(dev_status, DeviceStatusEnum.NETWORK_STATE_UNDEFINED.value)

        device.save(update_fields=("status",))

        if not device.is_noticeable:
            # print("Notification for %s is unnecessary" % device.ip_address or device.comment)
            return OldResponse({
                "text": "Notification for %s is unnecessary" % device.ip_address or device.comment
            })

        if not device.group:
            # print('Device has not have a group')
            return OldResponse({"text": "Device has not have a group"})

        recipients = UserProfile.objects.get_profiles_by_group(
            group_id=device.group.pk
        )
        # TODO: make editable UserProfile.flags
        # ).filter(
        #     flags=UserProfile.flags.notify_mon
        # )
        user_ids = tuple(recipient.pk for recipient in recipients.only("pk").iterator())

        notify_text = status_text_map.get(
            dev_status,
            "Device %(device_name)s getting undefined status code"
        )
        text = "%s\n\n%s" % (gettext(notify_text) % {
            "device_name": "{}({}) {}".format(device.ip_address or "", device.mac_addr, device.comment)
        }, message)
        # FIXME: make it done
        # ws_connector.send_data2ws({
        #     "eventType": "monitoring_event",
        #     "recipients": user_ids,
        #     "text": text
        # })
        notification_signal.send(
            sender=device.__class__,
            instance=device,
            recipients=user_ids,
            text=text
        )
        return OldResponse({
            "text": "notification successfully sent"
        })

    @action(detail=True)
    @catch_dev_manager_err
    def scan_mac_address_vlan(self, request, pk=None):
        dev = self.get_object()
        vid = safe_int(request.query_params.get("vid"))
        if vid == 0:
            return OldResponse("Valid vid required", status=status.HTTP_400_BAD_REQUEST)
        macs = dev.dev_read_mac_address_vlan(vid=vid)
        return OldResponse([asdict(m) for m in macs])

    @action(detail=True)
    @catch_dev_manager_err
    def scan_all_vlan_list(self, request, pk=None):
        dev = self.get_object()
        vlan_list = dev.dev_get_all_vlan_list()
        res = (asdict(i) for i in vlan_list)
        return OldResponse(res)

    @action(methods=['get'], detail=False)
    def device_types(self, request):
        dev_types = SwitchDeviceStrategyContext.get_device_types()
        result_dev_types = ({
            'v': uint,
            'nm': str(klass.description)
        } for uint, klass in dev_types.items())
        return OldResponse(result_dev_types)


class DeviceWithoutGroupListAPIView(DjingListAPIView):
    serializer_class = dev_serializers.DeviceWithoutGroupModelSerializer

    def get_queryset(self):
        qs = get_objects_for_user(self.request.user, perms="devices.view_device", klass=Device).order_by("id")
        return qs.filter(group=None)


class PortModelViewSet(DjingModelViewSet):
    queryset = Port.objects.annotate(user_count=Count("customer")).order_by("num")
    serializer_class = dev_serializers.PortModelSerializer
    filterset_fields = ("device", "num")

    @action(detail=True)
    @catch_dev_manager_err
    def toggle_port(self, request, pk=None):
        self.check_permission_code(request, "devices.can_toggle_ports")
        port_state = request.query_params.get("port_state")
        port_snmp_num = request.query_params.get("port_snmp_num")
        port_snmp_num = safe_int(port_snmp_num)
        port = self.get_object()
        if port_snmp_num > 0:
            port_num = port_snmp_num
        else:
            port_num = int(port.num)
        manager = port.device.get_switch_device_manager()
        if port_state == "up":
            manager.port_enable(port_num=port_num)
        elif port_state == "down":
            manager.port_disable(port_num=port_num)
        else:
            return OldResponse(_("Parameter port_state is bad"), status=status.HTTP_400_BAD_REQUEST)
        return OldResponse(status=status.HTTP_200_OK)

    # @action(detail=True)
    # @catch_dev_manager_err
    # def get_subscriber_on_port(self, request, pk=None):
    #     dev_id = request.query_params.get('device_id')
    #     # port = self.get_object()
    #     customers = Customer.objects.filter(device_id=dev_id, dev_port_id=pk)
    #     if not customers.exists():
    #         raise NotFound(gettext('Subscribers on port does not exist'))
    #     if customers.count() > 1:
    #         return OldResponse(customers)
    #     return OldResponse(self.serializer_class(instance=customers.first()))

    @action(detail=True)
    @catch_dev_manager_err
    def scan_mac_address_port(self, request, pk=None):
        port = self.get_object()
        dev = port.device
        if dev is None:
            return OldResponse(status=status.HTTP_404_NOT_FOUND)
        macs = tuple(dev.dev_switch_get_mac_address_port(device_port_num=port.num))
        return OldResponse(asdict(m) for m in macs)

    @action(detail=True)
    @catch_dev_manager_err
    def scan_vlan(self, request, pk=None):
        port = self.get_object()
        port_vlans = port.get_port_vlan_list()
        return OldResponse(asdict(p) for p in port_vlans)


class PortVlanMemberModelViewSet(DjingModelViewSet):
    queryset = PortVlanMemberModel.objects.all()
    serializer_class = dev_serializers.PortVlanMemberModelSerializer
    filterset_fields = ("vlanif", "port")


@api_view(['get'])
def groups_with_devices(request):
    grps = Group.objects.annotate(device_count=Count('device')).filter(device_count__gt=0).order_by('title')
    ser = dev_serializers.GroupsWithDevicesSerializer(instance=grps, many=True)
    return OldResponse(ser.data)

