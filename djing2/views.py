import re
from django.db.models import Q
from rest_framework.response import Response

from djing2 import MAC_ADDR_REGEX
from djing2.viewsets import DjingListAPIView
from customers.models import Customer
from devices.models import Device


def accs_format(acc: Customer, search_str: str) -> dict:
    r = {
        'id': acc.pk,
        'fio': acc.fio,
        'username': acc.username,
        't': 1
    }
    if acc.telephone:
        r.update({
            'telephone': acc.telephone
        })
    if acc.group:
        r.update({
            'gid': acc.group.pk
        })
    return r


def dev_format(device: Device, search_str: str) -> dict:
    r = {
        'id': device.pk,
        'text': device.comment,
        't': 2
    }
    if device.group:
        r.update({
            'gid': device.group.pk
        })
    return r


class SearchApiView(DjingListAPIView):
    # pagination_class = QueryPageNumberPagination
    # serializer_class = SearchSerializer

    def list(self, request, *args, **kwargs):
        s = request.GET.get('s')
        if not s:
            return Response(())
        s = s.replace('+', '')

        limit_count = 10

        if s:
            customers = Customer.objects.filter(
                Q(fio__icontains=s) | Q(username__icontains=s) |
                Q(telephone__icontains=s) |
                Q(additional_telephones__telephone__icontains=s) |
                Q(ip_address__icontains=s)
            )[:limit_count]

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
            'accounts': (accs_format(acc, s) for acc in customers),
            'devices': (dev_format(dev, s) for dev in devices)
        })
