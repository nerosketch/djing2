from django_filters.rest_framework import DjangoFilterBackend
from django.utils.translation import gettext_lazy as _
from django.db.utils import IntegrityError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from djing2.viewsets import DjingModelViewSet
from djing2.lib.mixins import SecureApiView
from djing2.lib import LogicError, DuplicateEntry, ProcessLocked
from networks.models import NetworkIpPool, VlanIf, CustomerIpLeaseModel
from networks.serializers import (NetworkIpPoolModelSerializer,
                                  VlanIfModelSerializer,
                                  CustomerIpLeaseModelSerializer)


class NetworkIpPoolModelViewSet(DjingModelViewSet):
    queryset = NetworkIpPool.objects.all()
    serializer_class = NetworkIpPoolModelSerializer
    filter_backends = (OrderingFilter, DjangoFilterBackend)
    ordering_fields = ('network', 'ip_start', 'ip_end', 'gateway')
    filterset_fields = ('groups',)

    @action(detail=True, methods=('post',))
    def group_attach(self, request, pk=None):
        network = self.get_object()
        gr = request.data.getlist('gr')
        network.groups.clear()
        network.groups.add(*gr)
        return Response(status=status.HTTP_200_OK)

    # @action(detail=True)
    # def selected_groups(self, request, pk=None):
    #     net = self.get_object()
    #     selected_grps = (pk[0] for pk in net.groups.only('pk').values_list('pk'))
    #     return Response(selected_grps)

    @action(methods=('get',), detail=True)
    def get_free_ip(self, request, pk=None):
        network = self.get_object()
        ip = network.get_free_ip()
        return Response(str(ip))


class VlanIfModelViewSet(DjingModelViewSet):
    queryset = VlanIf.objects.all()
    serializer_class = VlanIfModelSerializer
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    ordering_fields = ('title', 'vid')
    filterset_fields = ('device',)


class CustomerIpLeaseModelViewSet(DjingModelViewSet):
    queryset = CustomerIpLeaseModel.objects.all()
    serializer_class = CustomerIpLeaseModelSerializer
    filter_backends = (OrderingFilter, DjangoFilterBackend)
    filterset_fields = ('customer',)
    ordering_fields = ('ip_address', 'lease_time', 'mac_address')

    @action(methods=('get',), detail=True)
    def ping_ip(self, request, pk=None):
        lease = self.get_object()
        try:
            is_pinged = lease.ping_icmp()
            if not is_pinged:
                is_pinged = lease.ping_icmp(arp=True)
        except ProcessLocked:
            return Response({
                'text': _('Process locked by another process'),
                'status': False
            })
        return Response({
            'text': _('Ping ok') if is_pinged else _('no ping'),
            'status': is_pinged
        })


class DhcpLever(SecureApiView):
    #
    # Api view for dhcp event
    #
    http_method_names = ('get',)

    def get(self, request, format=None):
        del format
        data = request.query_params.copy()
        try:
            r = self.on_dhcp_event(data)
            if r is not None:
                if issubclass(r.__class__, Exception):
                    return Response({'error': str(r)})
                return Response({'text': r})
            return Response({'status': 'ok'})
        except IntegrityError as e:
            return Response({
                'status': str(e).replace('\n', ' ')
            })

    @staticmethod
    def on_dhcp_event(data: dict) -> str:
        """
        :param data = {
            'client_ip': ip_address('127.0.0.1'),
            'client_mac': 'aa:bb:cc:dd:ee:ff',
            'switch_mac': 'aa:bb:cc:dd:ee:ff',
            'switch_port': 3,
            'cmd': 'commit'
        }"""
        try:
            act = data.get('cmd')
            if act is None:
                return '"cmd" parameter is missing'
            client_ip = data.get('client_ip')
            if client_ip is None:
                return '"client_ip" parameter is missing'
            if act == 'commit':
                return CustomerIpLeaseModel.dhcp_commit_lease_add_update(
                    client_ip=client_ip, mac_addr=data.get('client_mac'),
                    dev_mac=data.get('switch_mac'), dev_port=data.get('switch_port')
                )
            elif act in ['expiry', 'release']:
                del_count, del_details = CustomerIpLeaseModel.objects.filter(ip_address=client_ip).delete()
                return "Removed: %d" % del_count
            else:
                return '"cmd" parameter is invalid: %s' % act
        except (LogicError, DuplicateEntry) as e:
            print('Error: %s:' % e.__class__.__name__, e)
            return str(e)
