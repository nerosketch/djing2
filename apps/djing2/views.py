import re
from ipaddress import ip_address, AddressValueError
from typing import Optional

from customers.models import Customer
from devices.models import Device
from django.conf import settings
from django.db.models import Q
from django.utils.translation import gettext
from django.contrib.sites.models import Site
from djing2 import IP_ADDR_REGEX, MAC_ADDR_REGEXP
from djing2.lib.fastapi.auth import is_admin_auth_dependency, TOKEN_RESULT_TYPE
from djing2.lib.fastapi.sites_depend import sites_dependency
from djing2.schemas import AccountSearchResponse, DeviceSearchResponse, SearchResultModel
from guardian.shortcuts import get_objects_for_user
from netaddr import EUI, mac_unix_expanded
from networks.models import CustomerIpLeaseModel
from fastapi import APIRouter, Depends, Request


router = APIRouter(
    tags=['Root']
)


def get_mac(mac: str) -> Optional[EUI]:
    try:
        return EUI(mac)
    except ValueError:
        pass


def is_mac_addr(mac: str, _ptrn=re.compile(MAC_ADDR_REGEXP)) -> bool:
    return bool(_ptrn.match(str(mac)))


def accs_format(acc: Customer) -> AccountSearchResponse:
    r = AccountSearchResponse(
        id=acc.pk,
        fio=acc.fio,
        username=acc.username,
        ips=list(acc.customeripleasemodel_set.select_related(
            "ip_address"
        ).values_list(
            "ip_address",
            flat=True
        )),
    )
    if acc.telephone:
        r.telephone = acc.telephone
    if acc.group:
        r.gid = acc.group_id
        r.group_title = acc.group.title
    return r


def dev_format(device: Device) -> DeviceSearchResponse:
    r = DeviceSearchResponse(
        id=device.pk,
        comment=device.comment,
        ip_address=device.ip_address,
        mac_addr=str(device.mac_addr),
        dev_type_str=device.get_dev_type_display(),
    )
    if device.group:
        r.gid = device.group_id
    return r


@router.get('/search/',
            dependencies=[],
            response_model=SearchResultModel,
            description=gettext(
                "Search customers and devices globally entire all system. "
                "Customer search provides by username, fio, and telephone. "
                "Devices search provides by ip address, mac address, "
                "and comment."
            )
            )
def search_entry_point(s: str = '', limit: int = 100,
                       auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
                       curr_site: Site = Depends(sites_dependency),
                       ):

    s = s.replace("+", "")
    if limit > 500:
        limit = 500

    if s:
        curr_user, token = auth
        customers = get_objects_for_user(
            curr_user,
            "customers.view_customer",
            klass=Customer,
        )
        # FIXME: move site filter to filter module
        if not curr_user.is_superuser:
            customers = customers.filter(sites__in=[curr_site])

        if re.match(IP_ADDR_REGEX, s):
            customers = customers.filter(
                customeripleasemodel__ip_address__icontains=s
            )
        elif is_mac_addr(s) and get_mac(s):
            mac = get_mac(s)
            customers = customers.filter(
                customeripleasemodel__mac_address__icontains=mac.format(
                    dialect=mac_unix_expanded
                )
            )
        else:
            customers = customers.filter(
                Q(fio__icontains=s)
                | Q(username__icontains=s)
                | Q(telephone__icontains=s)
                | Q(additional_telephones__telephone__icontains=s)
                | Q(description__icontains=s)
            )
        customers = customers.select_related("group")[:limit]

        devices = get_objects_for_user(
            curr_user,
            "devices.view_device",
            klass=Device,
        )
        # FIXME: move site filter to filter module
        if not curr_user.is_superuser:
            devices = devices.filter(sites__in=[curr_site])

        if is_mac_addr(s) and get_mac(s):
            mac = get_mac(s)
            str_mac = mac.format(dialect=mac_unix_expanded)
            devices = devices.filter(mac_addr=str_mac)[:limit]
        else:
            devices = devices.filter(
                Q(comment__icontains=s) | Q(ip_address__icontains=s)
            )[:limit]
    else:
        customers = ()
        devices = ()

    return SearchResultModel(
        accounts=(accs_format(acc) for acc in customers.distinct()),
        devices=(dev_format(dev) for dev in devices.distinct())
    )


@router.get('/can_login_by_location/', response_model=bool)
def can_login_by_location(r: Request):
    """Can account login by his ip address."""
    try:
        remote_ip = ip_address(r.client.host)
        if remote_ip.version == 4:
            ips_exists = CustomerIpLeaseModel.objects.filter(ip_address=str(remote_ip)).exists()
            return ips_exists
    except AddressValueError:
        pass
    return False


@router.get('/get_vapid_public_key/', response_model=Optional[str])
def get_vapid_public_key(request: Request):
    """Get VAPID public key for push."""

    opts = getattr(settings, "WEBPUSH_SETTINGS")
    if opts is None or not isinstance(opts, dict):
        return
    vpk = opts.get("VAPID_PUBLIC_KEY")
    return vpk
