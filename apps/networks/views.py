from django_filters.rest_framework import DjangoFilterBackend
from django.utils.translation import gettext_lazy as _
from django.db.utils import IntegrityError
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from djing2.lib.filters import CustomObjectPermissionsFilter
from djing2.lib.ws_connector import WsEventTypeEnum, send_data2ws, WebSocketSender
from djing2.viewsets import DjingModelViewSet
from djing2.lib.mixins import SecureApiViewMixin, SitesGroupFilterMixin, SitesFilterMixin
from djing2.lib.logger import logger
from djing2.lib import LogicError, DuplicateEntry, ProcessLocked
from networks.models import NetworkIpPool, VlanIf, CustomerIpLeaseModel
from networks import serializers
from customers.serializers import CustomerModelSerializer


def _update_lease_send_ws_signal(customer_id: int, s2ws=None):
    if s2ws is None:
        s2ws = send_data2ws
    s2ws({"eventType": WsEventTypeEnum.UPDATE_CUSTOMER_LEASES.value, "data": {"customer_id": customer_id}})


class NetworkIpPoolModelViewSet(SitesGroupFilterMixin, DjingModelViewSet):
    queryset = NetworkIpPool.objects.select_related("vlan_if")
    serializer_class = serializers.NetworkIpPoolModelSerializer
    filter_backends = (CustomObjectPermissionsFilter, OrderingFilter, DjangoFilterBackend)
    ordering_fields = ("network", "ip_start", "ip_end", "gateway")
    filterset_fields = ("groups",)

    @action(detail=True, methods=["post"])
    def group_attach(self, request, pk=None):
        network = self.get_object()
        gr = request.data.getlist("gr")
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
            sites=[self.request.site],
            *args, **kwargs
        )


class FindCustomerByCredentials(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    http_method_names = ('get',)

    def get(self, request, format=None):
        request_serializer = serializers.FindCustomerByDeviceCredentialsParams(
            data=request.query_params,
            context={'request': request}
        )
        request_serializer.is_valid(raise_exception=True)
        customer = NetworkIpPool.find_customer_by_device_credentials(
            device_mac=request_serializer.data.get('mac'),
            device_port=request_serializer.data.get('dev_port')
        )
        if not customer:
            return Response('Not found', status=status.HTTP_404_NOT_FOUND)
        ser = CustomerModelSerializer(instance=customer, context={
            'request': request
        })
        return Response(ser.data)


class VlanIfModelViewSet(SitesFilterMixin, DjingModelViewSet):
    queryset = VlanIf.objects.all().order_by('vid')
    serializer_class = serializers.VlanIfModelSerializer
    filter_backends = (CustomObjectPermissionsFilter, DjangoFilterBackend, OrderingFilter)
    ordering_fields = ("title", "vid")
    filterset_fields = ("device",)

    def perform_create(self, serializer, *args, **kwargs):
        return super().perform_create(serializer=serializer, sites=[self.request.site])


class CustomerIpLeaseModelViewSet(DjingModelViewSet):
    queryset = CustomerIpLeaseModel.objects.all()
    serializer_class = serializers.CustomerIpLeaseModelSerializer
    filter_backends = (CustomObjectPermissionsFilter, OrderingFilter, DjangoFilterBackend)
    filterset_fields = ("customer",)
    ordering_fields = ("ip_address", "lease_time", "mac_address")

    @action(detail=True)
    def ping_ip(self, request, pk=None):
        lease = self.get_object()
        text = _("Ping ok")
        try:
            is_pinged = lease.ping_icmp()
            if not is_pinged:
                arping_enabled = getattr(settings, "ARPING_ENABLED", False)
                if arping_enabled and lease.ping_icmp(arp=True):
                    text = _("arp ping ok")
                else:
                    text = _("no ping")
        except ProcessLocked:
            return Response({"text": _("Process locked by another process"), "status": False})
        except ValueError as err:
            return Response({"text": str(err), "status": False})
        return Response({"text": text, "status": is_pinged})


class DhcpLever(SecureApiViewMixin, APIView):
    #
    # Api view for dhcp event
    #
    http_method_names = ["get"]

    def get(self, request, format=None):
        data = request.query_params.copy()
        try:
            r = self.on_dhcp_event(data)
            if r is not None:
                if issubclass(r.__class__, Exception):
                    return Response({"error": str(r)})
                return Response({"text": r})
            return Response({"status": "ok"})
        except IntegrityError as e:
            return Response({"status": str(e).replace("\n", " ")})

    @staticmethod
    def on_dhcp_event(data: dict) -> str:
        """
        Data variable can take this form.
        >>> data = {
        ...    'client_ip': ip_address('127.0.0.1'),
        ...    'client_mac': 'aa:bb:cc:dd:ee:ff',
        ...    'switch_mac': 'aa:bb:cc:dd:ee:ff',
        ...    'switch_port': 3,
        ...    'cmd': 'commit'
        ... }
        """
        try:
            data_action = data.get("cmd")
            if data_action is None:
                return '"cmd" parameter is missing'
            client_ip = data.get("client_ip")
            if client_ip is None:
                return '"client_ip" parameter is missing'
            if data_action == "commit":
                res = CustomerIpLeaseModel.lease_commit_add_update(
                    client_ip=client_ip,
                    mac_addr=data.get("client_mac"),
                    dev_mac=data.get("switch_mac"),
                    dev_port=data.get("switch_port"),
                )
                # lease_id, ip_addr, pool_id, lease_time, mac_addr, customer_id, is_dynamic, last_update = res
                ip_addr = res[1]
                customer_id = res[5]
                _update_lease_send_ws_signal(customer_id)
                return "Assigned %s" % (ip_addr or "null")
            elif data_action in ["expiry", "release"]:
                leases = CustomerIpLeaseModel.objects.filter(ip_address=client_ip)

                # TODO: May be async
                with WebSocketSender() as send2ws:
                    customer_uids = (lease.customer_id for lease in leases.iterator())
                    for customer_uid in customer_uids:
                        _update_lease_send_ws_signal(customer_uid, send2ws)
                del_count, del_details = leases.delete()
                return "Removed: %d" % del_count
            else:
                return '"cmd" parameter is invalid: %s' % data_action
        except (LogicError, DuplicateEntry) as e:
            logger.error("%s: %s" % (e.__class__.__name__, e))
            return str(e)
