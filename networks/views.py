from django_filters.rest_framework import DjangoFilterBackend
from django.utils.translation import gettext_lazy as _
from django.db.utils import IntegrityError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from djing2.lib.filters import CustomObjectPermissionsFilter
from djing2.viewsets import DjingModelViewSet
from djing2.lib.mixins import SecureApiView, SitesGroupFilterMixin, SitesFilterMixin
from djing2.lib import LogicError, DuplicateEntry, ProcessLocked
from networks.models import NetworkIpPool, VlanIf, CustomerIpLeaseModel
from networks.serializers import (NetworkIpPoolModelSerializer,
                                  VlanIfModelSerializer,
                                  CustomerIpLeaseModelSerializer)


class NetworkIpPoolModelViewSet(SitesGroupFilterMixin, DjingModelViewSet):
    queryset = NetworkIpPool.objects.select_related('vlan_if')
    serializer_class = NetworkIpPoolModelSerializer
    filter_backends = (CustomObjectPermissionsFilter, OrderingFilter, DjangoFilterBackend)
    ordering_fields = ('network', 'ip_start', 'ip_end', 'gateway')
    filterset_fields = ('groups',)

    @action(detail=True, methods=['post'])
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

    @action(detail=True)
    def get_free_ip(self, request, pk=None):
        network = self.get_object()
        ip = network.get_free_ip()
        return Response(str(ip))

    def perform_create(self, serializer, *args, **kwargs):
        return super().perform_create(
            serializer=serializer,
            sites=[self.request.site]
        )


class VlanIfModelViewSet(SitesFilterMixin, DjingModelViewSet):
    queryset = VlanIf.objects.all()
    serializer_class = VlanIfModelSerializer
    filter_backends = (CustomObjectPermissionsFilter, DjangoFilterBackend, OrderingFilter)
    ordering_fields = ('title', 'vid')
    filterset_fields = ('device',)

    def perform_create(self, serializer, *args, **kwargs):
        return super().perform_create(
            serializer=serializer,
            sites=[self.request.site]
        )


class CustomerIpLeaseModelViewSet(DjingModelViewSet):
    queryset = CustomerIpLeaseModel.objects.all()
    serializer_class = CustomerIpLeaseModelSerializer
    filter_backends = (CustomObjectPermissionsFilter, OrderingFilter, DjangoFilterBackend)
    filterset_fields = ('customer',)
    ordering_fields = ('ip_address', 'lease_time', 'mac_address')

    @action(detail=True)
    def ping_ip(self, request, pk=None):
        lease = self.get_object()
        text = _('Ping ok')
        try:
            is_pinged = lease.ping_icmp()
            if not is_pinged:
                is_pinged = lease.ping_icmp(arp=True)
                if is_pinged:
                    text = _('arp ping ok')
                else:
                    text = _('no ping')
        except ProcessLocked:
            return Response({
                'text': _('Process locked by another process'),
                'status': False
            })
        except ValueError as err:
            return Response({
                'text': str(err),
                'status': False
            })
        return Response({
            'text': text,
            'status': is_pinged
        })


class DhcpLever(SecureApiView):
    #
    # Api view for dhcp event
    #
    http_method_names = ['get']

    def get(self, request, format=None):
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
            data_action = data.get('cmd')
            if data_action is None:
                return '"cmd" parameter is missing'
            client_ip = data.get('client_ip')
            if client_ip is None:
                return '"client_ip" parameter is missing'
            if data_action == 'commit':
                return CustomerIpLeaseModel.lease_commit_add_update(
                    client_ip=client_ip, mac_addr=data.get('client_mac'),
                    dev_mac=data.get('switch_mac'), dev_port=data.get('switch_port')
                )
            elif data_action in ['expiry', 'release']:
                del_count, del_details = CustomerIpLeaseModel.objects.filter(ip_address=client_ip).delete()
                return "Removed: %d" % del_count
            else:
                return '"cmd" parameter is invalid: %s' % data_action
        except (LogicError, DuplicateEntry) as e:
            print('Error: %s:' % e.__class__.__name__, e)
            return str(e)
