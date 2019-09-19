import re

from django.db.models import Q
from django.utils.html import escape
from django.conf import settings
from rest_framework.response import Response

from djing2 import MAC_ADDR_REGEX
from djing2.viewsets import DjingListAPIView
from customers.models import Customer
from devices.models import Device


REST_FRAMEWORK = getattr(settings, 'REST_FRAMEWORK', 15)


def replace_without_case(orig, old, new):
    return re.sub(old, new, orig, flags=re.IGNORECASE)


def accs_format(acc: Customer, search_str: str) -> dict:
    r = {
        'id': acc.pk,
        'fio': replace_without_case(escape(acc.fio), search_str, "<b>%s</b>" % search_str),
        'username': replace_without_case(escape(acc.username), search_str, "<b>%s</b>" % search_str)
    }
    tel = replace_without_case(escape(acc.telephone), search_str, "<b>%s</b>" % search_str)
    if tel:
        r.update({
            'telephone': tel
        })
    return r


def dev_format(device: Device, search_str: str) -> dict:
    return {
        'id': device.pk,
        'text': replace_without_case(escape(device.comment), search_str, "<b>%s</b>" % search_str),
    }


class SearchApiView(DjingListAPIView):
    # pagination_class = QueryPageNumberPagination
    # serializer_class = SearchSerializer

    def list(self, request, *args, **kwargs):
        s = request.GET.get('s')
        if not s:
            return Response(())
        s = s.replace('+', '')

        limit_count = REST_FRAMEWORK.get('PAGE_SIZE')

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
