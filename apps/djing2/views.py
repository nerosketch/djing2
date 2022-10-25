import re
from ipaddress import ip_address, AddressValueError
from typing import Optional

from customers.models import Customer
from devices.models import Device
from django.conf import settings
from django.db.models import Q
from django.utils.translation import gettext
from djing2 import IP_ADDR_REGEX
from djing2.serializers import SearchSerializer
from djing2.viewsets import DjingListAPIView
from guardian.shortcuts import get_objects_for_user
from netaddr import EUI, mac_unix_expanded
from networks.models import CustomerIpLeaseModel
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response


def get_mac(mac: str) -> Optional[EUI]:
    try:
        return EUI(mac)
    except ValueError:
        pass


def accs_format(acc: Customer) -> dict:
    r = {
        "id": acc.pk,
        "fio": acc.fio,
        "username": acc.username,
        "ips": acc.customeripleasemodel_set.select_related("ip_address").values_list("ip_address", flat=True),
    }
    if acc.telephone:
        r.update({"telephone": acc.telephone})
    if acc.group:
        r.update({"gid": acc.group.pk, "group_title": acc.group.title})
    return r


def dev_format(device: Device) -> dict:
    r = {
        "id": device.pk,
        "comment": device.comment,
        "ip_address": device.ip_address,
        "mac_addr": str(device.mac_addr),
        "dev_type_str": device.get_dev_type_display(),
    }
    if device.group:
        r.update({"gid": device.group.pk})
    return r


class SearchApiView(DjingListAPIView):
    # pagination_class = QueryPageNumberPagination
    serializer_class = SearchSerializer
    __doc__ = gettext(
        "Search customers and devices globally entire all system. "
        "Customer search provides by username, fio, and telephone. "
        "Devices search provides by ip address, mac address, "
        "and comment."
    )

    def list(self, request, *args, **kwargs):
        s = request.GET.get("s")
        if not s:
            return Response(())
        s = s.replace("+", "")

        limit_count = 100

        if s:
            customers = get_objects_for_user(
                request.user,
                "customers.view_customer",
                klass=Customer,
            )
            # FIXME: move site filter to filter module
            if not request.user.is_superuser:
                customers = customers.filter(sites__in=[self.request.site])

            mac = get_mac(s)
            if re.match(IP_ADDR_REGEX, s):
                customers = customers.filter(
                    customeripleasemodel__ip_address__icontains=s
                )
            elif isinstance(mac, EUI):
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
            customers = customers.select_related("group")[:limit_count]

            devices = get_objects_for_user(
                request.user,
                "devices.view_device",
                klass=Device,
            )
            # FIXME: move site filter to filter module
            if not request.user.is_superuser:
                devices = devices.filter(sites__in=[self.request.site])

            if isinstance(mac, EUI):
                str_mac = mac.format(dialect=mac_unix_expanded)
                devices = devices.filter(mac_addr=str_mac)[:limit_count]
            else:
                devices = devices.filter(Q(comment__icontains=s) | Q(ip_address__icontains=s))[:limit_count]
        else:
            customers = ()
            devices = ()

        return Response(
            {"accounts": (accs_format(acc) for acc in customers), "devices": (dev_format(dev) for dev in devices)}
        )


@api_view()
@authentication_classes([])
@permission_classes([])
def can_login_by_location(request):
    """Can account login by his ip address."""
    try:
        remote_ip = ip_address(request.META.get("HTTP_X_REAL_IP"))
        if remote_ip.version == 4:
            ips_exists = CustomerIpLeaseModel.objects.filter(ip_address=str(remote_ip)).exists()
            return Response(ips_exists)

    except AddressValueError:
        pass
    return Response(False)


@api_view()
@authentication_classes([])
@permission_classes([])
def get_vapid_public_key(request):
    """Get VAPID public key for push."""
    opts = getattr(settings, "WEBPUSH_SETTINGS")
    if opts is None or not isinstance(opts, dict):
        return Response()
    vpk = opts.get("VAPID_PUBLIC_KEY")
    return Response(vpk)
