import base64
from typing import Tuple, Optional
from ipaddress import ip_interface, ip_network

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.lib import safe_int, macbin2str
from djing2.viewsets import DjingAuthorizedViewSet
from networks.exceptions import DhcpRequestError
from networks.models import CustomerIpLeaseModel, DHCP_DEFAULT_LEASE_TIME
from networks.serializers.radius import RadiusDHCPRequestSerializer


def catch_radius_errs(fn):
    def _wrapper(self, *args, **kwargs):
        try:
            return fn(self, *args, **kwargs)
        except DhcpRequestError as err:
            return Response(str(err), status=status.HTTP_404_NOT_FOUND)

    # Hack for decorator @action
    _wrapper.__name__ = fn.__name__
    return _wrapper


def _parse_opt82(remote_id: bytes, circuit_id: bytes) -> Tuple[Optional[str], int]:
    # 'remote_id': '0x000600ad24d0c544', 'circuit_id': '0x000400020002'
    mac, port = None, 0
    if circuit_id.startswith(b'ZTE'):
        mac = remote_id.decode()
    else:
        try:
            port = safe_int(circuit_id[-1:][0])
        except IndexError:
            port = 0
        if len(remote_id) >= 6:
            mac = macbin2str(remote_id[-6:])
    return mac, port


def _return_bad_response(text: str):
    return Response({
        "control:Auth-Type": 'Reject',
        "Reply-Message": text
    }, status.HTTP_403_FORBIDDEN)


def _clear_ip(ip):
    return str(ip_interface(ip).ip)


class RadiusDHCPRequestViewSet(DjingAuthorizedViewSet):
    serializer_class = RadiusDHCPRequestSerializer

    # def dispatch(self, request: http.HttpRequest, *args: Any, **kwargs: Any):

    def _show_serializer(self):
        serializer = self.get_serializer()
        return Response(serializer.data)

    def _check_data(self, data):
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.data

    @action(methods=('post', 'get'), detail=False)
    @catch_radius_errs
    def dhcp_request(self, request, *args, **kwargs):
        if request.method == 'GET':
            return self._show_serializer()
        data = self._check_data(request.data)

        opt82 = data.get('opt82')
        remote_id = base64.b64decode(opt82.get('remote_id', ''))
        circuit_id = base64.b64decode(opt82.get('circuit_id', ''))
        user_mac = data.get('client_mac')

        # try to get switch mac addr
        if not all([remote_id, circuit_id]):
            return _return_bad_response('Bad option82')
        dev_mac, dev_port = _parse_opt82(remote_id, circuit_id)
        if dev_mac is None:
            return _return_bad_response('Failed to parse option82')

        # If customer has an active leases then return latest.
        # If not found then assign new
        ip_lease = CustomerIpLeaseModel.fetch_subscriber_lease(
            customer_mac=user_mac,
            device_mac=dev_mac,
            device_port=dev_port,
            is_dynamic=True
        )

        if ip_lease is None:
            return _return_bad_response("Can't issue a lease")
        pool_contains_ip = ip_lease.pool
        net = ip_network(pool_contains_ip.network)

        return Response(data={
            "ip": _clear_ip(ip_lease.ip_address),
            "mask": str(net.netmask),
            "gw": _clear_ip(pool_contains_ip.gateway),
            # "dns": '10.12.1.4',
            "lease_time": DHCP_DEFAULT_LEASE_TIME
        })
