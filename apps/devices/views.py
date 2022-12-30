import re
from functools import wraps
from json import dumps as json_dumps
from dataclasses import asdict
from typing import Optional

from django.contrib.sites.models import Site
from django.db.models import Count, QuerySet, Q
from django.db import transaction
from django.utils.translation import gettext as _
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

from fastapi import APIRouter, Request, Depends, Response, Path, HTTPException
from starlette.responses import StreamingResponse

from djing2.lib.fastapi.auth import is_admin_auth_dependency, TOKEN_RESULT_TYPE
from djing2.lib.filters import CustomSearchFilter, filter_qs_by_fields_dependency, search_qs_by_fields_dependency
from devices import serializers as dev_serializers
from devices.device_config.pon.pon_device_strategy import PonOLTDeviceStrategyContext
from devices.device_config.switch.switch_device_strategy import SwitchDeviceStrategyContext
from devices.models import Device, Port, PortVlanMemberModel, DeviceStatusEnum
from devices.device_config.base import (
    DeviceImplementationError,
    DeviceConnectionError,
    UnsupportedReadingVlan,
    DeviceTimeoutError,
    Vlans,
    OptionalScriptCallResult,
    DeviceOnuConfigTemplateSchema,
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


def device_with_perm_dep(perm: str):
    def _wrapped(
        device_id: int = Path(gt=0),
        curr_user: UserProfile = Depends(permission_check_dependency(
            perm_codename=perm
        )),
        curr_site: Site = Depends(sites_dependency),
    ):
        qs = general_filter_queryset(
            qs_or_model=Device,
            curr_site=curr_site,
            curr_user=curr_user,
            perm_codename=perm,
        )
        device = get_object_or_404(qs, pk=device_id)
        return device
    return _wrapped


def device_object_dependency(
    device: Device = Depends(device_with_perm_dep(perm='devices.view_device'))
) -> Device:
    return device


@router.get('/pon/{device_id}/scan_units_unregistered/',
            response_model=list)
def scan_units_unregistered(device: Device = Depends(device_object_dependency)):
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


@router.get('/pon/{device_id}/scan_olt_fibers/')
def scan_olt_fibers(
    device: Device = Depends(device_object_dependency)
):
    manager = device.get_pon_olt_device_manager()
    if hasattr(manager, "get_fibers"):
        fb = manager.get_fibers()
        return tuple(fb)
    return Response({"Error": {"text": "Manager has not get_fibers attribute"}})


@router.get('/pon/{device_id}/scan_pon_details/',
            response_model=dict)
def scan_pon_details(
    device: Device = Depends(device_object_dependency)
):
    pon_manager = device.get_pon_onu_device_manager()
    data = pon_manager.get_details()
    return data


@router.get('/pon/{device_id}/scan_onu_list/')
def scan_onu_list(
    device: Device = Depends(device_object_dependency)
):
    manager = device.get_pon_olt_device_manager()
    if not isinstance(manager, PonOLTDeviceStrategyContext):
        raise DeviceImplementationError("Expected PonOLTDeviceStrategyContext instance")

    def chunk_cook(chunk: dict) -> bytes:
        chunk_json = json_dumps(chunk, ensure_ascii=False, cls=JSONEncoder)
        chunk_json = "%s\n" % chunk_json
        format_string = "{:%ds}" % chunk_max_len

        # FIXME: STR100: Calling format with insecure string. Found in 'format_string.format(chunk_json)'.
        dat = format_string.format(chunk_json)
        return dat.encode()[:chunk_max_len]

    try:
        onu_list = manager.scan_onu_list()
        item_size = next(onu_list)
        chunk_max_len = next(onu_list)
        r = StreamingResponse(
            content=(
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
            ),
            status_code=status.HTTP_200_OK,
            media_type="application/octet-stream",
            headers={
                "Content-Length": str(item_size * chunk_max_len),
                # "Cache-Control": "no-store",
            }
        )
        return r
    except StopIteration:
        pass
    return Response("No all fetched")


@router.get('/pon/{device_id}/scan_onu_on_fiber/{fiber_num}',
            response_model=list)
def scan_onu_on_fiber(
    fiber_num: int = Path(gt=0),
    device: Device = Depends(device_object_dependency)
):
    manager = device.get_pon_olt_device_manager()
    if hasattr(manager, "get_ports_on_fiber"):
        try:
            onu_list = tuple(manager.get_ports_on_fiber(fiber_num=fiber_num))
            return onu_list
        except ProcessLocked:
            raise HTTPException(
                detail=_("Process locked by another process"),
                status_code=452
            )
    raise HTTPException(
        detail={"Error": {"text": 'Manager has not "get_ports_on_fiber" attribute'}},
        status_code=status.HTTP_200_OK
    )


@router.get('/pon/{device_id}/fix_onu/',
            response_model=schemas.FixOnuResponseSchema)
def fix_onu(
    onu: Device = Depends(device_with_perm_dep(perm='devices.can_fix_onu'))
):
    fix_status, text = onu.fix_onu()
    return schemas.FixOnuResponseSchema(
        text=text,
        status=1 if fix_status else 2,
        device=schemas.DevicePONModelSchema.from_orm(onu)
    )


@router.get('/pon/{device_id}/remove_from_olt/',
            response_model=schemas.RemoveFromOLTResponseSchema)
def remove_from_olt(
    request: Request,
    device: Device = Depends(device_with_perm_dep(perm='devices.can_remove_from_olt'))
):
    args = request.query_params
    if device.remove_from_olt(**args):
        return schemas.RemoveFromOLTResponseSchema(
            text=_("Deleted"),
            status=1
        )
    return schemas.RemoveFromOLTResponseSchema(
        text=_("Failed"),
        status=2
    )


@router.get('/pon/{device_id}/get_onu_config_options/')
def get_onu_config_options(
    device: Device = Depends(device_object_dependency)
):
    config_types = device.get_config_types()
    config_choices = (i.to_dict() for i in config_types if i)
    # klass = dev.get_manager_klass()

    return {
        # 'port_num': klass.ports_len,
        "config_choices": config_choices,
        # 'accept_vlan': True or not True  # or not to be :)
    }


@router.get('/pon/{device_id}/read_onu_vlan_info/',
            response_model=Vlans)
def read_onu_vlan_info(
    device: Device = Depends(device_object_dependency)
) -> Vlans:
    try:
        if device.is_onu_registered:
            vlans = tuple(device.read_onu_vlan_info())
        else:
            vlans = device.default_vlan_info()
        return vlans
    except UnsupportedReadingVlan:
        # Vlan config unsupported
        return ()


@router.post('/pon/{device_id}/apply_device_onu_config_template/',
             response_model=OptionalScriptCallResult)
def apply_device_onu_config_template(
    device_config_data: DeviceOnuConfigTemplateSchema,
    device: Device = Depends(device_with_perm_dep(perm='devices.can_apply_onu_config'))
) -> OptionalScriptCallResult:
    res = device.apply_onu_config(config=device_config_data)
    return res


@router.get(
    '/all/',
    response_model=IListResponse[schemas.DeviceModelSchema],
    response_model_exclude_none=True
)
@paginate_qs_path_decorator(
    schema=schemas.DeviceModelSchema,
    db_model=Device
)
def get_all_devices(
    request: Request,
    pagination: Pagination = Depends(),
    curr_site: Site = Depends(sites_dependency),
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='devices.view_device'
    )),
    filter_fields_q: Q = Depends(filter_qs_by_fields_dependency(
        fields={
            'group': int, 'dev_type': int, 'status': int, 'is_noticeable': bool,
            'address': int
        },
        db_model=Device
    )),
    search_filter_q: Q = Depends(search_qs_by_fields_dependency(
        search_fields=["comment", "ip_address", "mac_addr"]
    )),
    dev_initial_qs: QuerySet[Device] = Depends(filter_query_set_dependency)
):
    queryset = general_filter_queryset(
        qs_or_model=dev_initial_qs,
        curr_site=curr_site,
        curr_user=curr_user,
        perm_codename='devices.view_device',
    )
    queryset = queryset.filter(filter_fields_q | search_filter_q)
    return queryset


@router.post(
    '/all/',
    response_model=schemas.DeviceModelSchema,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED
)
def add_new_device(
    dev_info: schemas.DeviceBaseSchema,
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='devices.add_device'
    )),
    curr_site: Site = Depends(sites_dependency),
):
    pdata = dev_info.dict(exclude_unset=True)
    with transaction.atomic():
        dev = Device.objects.create(**pdata)
        dev.sites.add(curr_site)
        curr_user.log(
            do_type=UserProfileLogActionType.CREATE_DEVICE,
            additional_text='ip %s, mac: %s, "%s"' % (
                dev.ip_address,
                dev.mac_addr,
                dev.comment
            )
        )
    return schemas.DeviceModelSchema.from_orm(dev)


@router.delete(
    '/all/{device_id}/',
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_device(
    device: Device = Depends(device_with_perm_dep(perm='devices.delete_device')),
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='devices.delete_device'
    )),
):
    with transaction.atomic():
        device.delete()
        # log about it
        curr_user.log(
            do_type=UserProfileLogActionType.DELETE_DEVICE,
            additional_text='ip %s, mac: %s, "%s"' % (
                device.ip_address or "-",
                device.mac_addr or "-",
                device.comment or "-"
            ),
        )


class DeviceModelViewSet(DjingModelViewSet):
    queryset = Device.objects.select_related("parent_dev").order_by('comment')
    serializer_class = dev_serializers.DeviceModelSerializer
    filterset_fields = ("group", "dev_type", "status", "is_noticeable", "address")
    filter_backends = (CustomObjectPermissionsFilter, CustomSearchFilter, DjangoFilterBackend)
    ordering_fields = ("ip_address", "mac_addr", "comment", "dev_type")

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
            # print('Device has not had a group')
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
        text = "%s\n\n%s" % (_(notify_text) % {
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
    return OldResponse({
        'results': ser.data
    })

