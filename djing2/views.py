import re
from ipaddress import ip_address, AddressValueError
from django.db.models import Q
from guardian.shortcuts import get_objects_for_user
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.response import Response

from djing2 import MAC_ADDR_REGEX, IP_ADDR_REGEX
from djing2.serializers import SearchSerializer
from djing2.viewsets import DjingListAPIView
from customers.models import Customer
from devices.models import Device
from networks.models import CustomerIpLeaseModel


def accs_format(acc: Customer) -> dict:
    r = {
        'id': acc.pk,
        'fio': acc.fio,
        'username': acc.username,
        'ips': acc.customeripleasemodel_set.select_related('ip_address').values_list('ip_address', flat=True)
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
            customers = get_objects_for_user(
                request.user,
                'customers.view_customer', klass=Customer
            )
            if re.match(IP_ADDR_REGEX, s):
                customers = customers.filter(
                    Q(customeripleasemodel__ip_address__icontains=s) |
                    Q(ip_address__icontains=s)
                )
            else:
                customers = customers.filter(
                    Q(fio__icontains=s) | Q(username__icontains=s) |
                    Q(telephone__icontains=s) |
                    Q(additional_telephones__telephone__icontains=s) |
                    Q(ip_address__icontains=s)
                )
            customers = customers.select_related('group')[:limit_count]

            devices = get_objects_for_user(
                request.user,
                'devices.view_device', klass=Device
            )
            if re.match(MAC_ADDR_REGEX, s):
                devices = devices.filter(mac_addr=s)[:limit_count]
            else:
                devices = devices.filter(
                    Q(comment__icontains=s) | Q(ip_address__icontains=s)
                )[:limit_count]
        else:
            customers = ()
            devices = ()

        return Response({
            'accounts': (accs_format(acc) for acc in customers),
            'devices': (dev_format(dev) for dev in devices)
        })


@api_view()
@authentication_classes([])
@permission_classes([])
def can_login_by_location(request):
    try:
        remote_ip = ip_address(request.META.get('REMOTE_ADDR'))
        if remote_ip.version == 4:
            ips_count = CustomerIpLeaseModel.objects.filter(
                ip_address=str(remote_ip)
            ).count()
            if ips_count == 1:
                return Response(True)
            has_exist = Customer.objects.filter(
                ip_address=str(remote_ip),
                is_active=True
            ).exists()
            return Response(has_exist)
    except AddressValueError:
        pass
    return Response(False)
