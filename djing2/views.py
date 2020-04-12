import re
from ipaddress import ip_address, AddressValueError
from django.db.models import Q
from rest_framework.decorators import api_view
from rest_framework.response import Response

from djing2 import MAC_ADDR_REGEX
from djing2.serializers import SearchSerializer
from djing2.viewsets import DjingListAPIView
from customers.models import Customer
from devices.models import Device


def accs_format(acc: Customer) -> dict:
    r = {
        'id': acc.pk,
        'fio': acc.fio,
        'username': acc.username
    }
    if acc.telephone:
        r.update({
            'telephone': acc.telephone
        })
    if acc.group:
        r.update({
            'gid': acc.group.pk,
            'group_title': acc.group.title
        })
    return r


def dev_format(device: Device) -> dict:
    r = {
        'id': device.pk,
        'comment': device.comment,
        'ip_address': device.ip_address,
        'mac_addr': str(device.mac_addr),
        'dev_type_str': device.get_dev_type_display()
    }
    if device.group:
        r.update({
            'gid': device.group.pk
        })
    return r


class SearchApiView(DjingListAPIView):
    # pagination_class = QueryPageNumberPagination
    serializer_class = SearchSerializer

    def list(self, request, *args, **kwargs):
        s = request.GET.get('s')
        if not s:
            return Response(())
        s = s.replace('+', '')

        limit_count = 100

        if s:
            customers = Customer.objects.filter(
                Q(fio__icontains=s) | Q(username__icontains=s) |
                Q(telephone__icontains=s) |
                Q(additional_telephones__telephone__icontains=s) |
                Q(ip_address__icontains=s)
            ).select_related('group')[:limit_count]

            if re.match(MAC_ADDR_REGEX, s):
                devices = Device.objects.filter(mac_addr=s)[:limit_count]
            else:
                devices = Device.objects.filter(
                    Q(comment__icontains=s) | Q(ip_address__icontains=s)
                )[:limit_count]
        else:
            customers = ()
            devices = ()

        return Response({
            'accounts': (accs_format(acc) for acc in customers),
            'devices': (dev_format(dev) for dev in devices)
        })


@api_view(http_method_names=['get'])
def can_login_by_location(request):
    try:
        remote_ip = ip_address(request.META.get('REMOTE_ADDR'))
        if remote_ip.version == 4:
            has_exist = Customer.objects.filter(
                ip_address=str(remote_ip),
                is_active=True
            ).exists()
            return Response(has_exist)
    except AddressValueError:
        pass
    return Response(False)
