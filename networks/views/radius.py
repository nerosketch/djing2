from datetime import datetime
from typing import Tuple, Optional

from django.core.exceptions import MultipleObjectsReturned
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.lib import safe_int, macbin2str
from djing2.viewsets import DjingAuthorizedViewSet
from customers.models.customer import Customer
from devices.models import Device, Port
from networks.models import CustomerIpLeaseModel, DHCP_DEFAULT_LEASE_TIME, NetworkIpPool
from networks.serializers.net import NetworkIpPoolModelSerializer
from networks.serializers.radius import RadiusDHCPRequestSerializer


def _parse_opt82(remote_id: bytes, circuit_id: bytes) -> Tuple[Optional[str], int]:
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
    return {
        "control:Auth-Type": 'Reject',
        "Reply-Message": text
    }, status.HTTP_403_FORBIDDEN


class RadiusDHCPRequestViewSet(DjingAuthorizedViewSet):
    serializer_class = RadiusDHCPRequestSerializer

    # def dispatch(self, request: http.HttpRequest, *args: Any, **kwargs: Any):

    @staticmethod
    def dhcp_get_customer_by_opt82(client_ip: str, client_mac: str,
                                   switch_mac: str, switch_port: int):
        try:
            dev = Device.objects.get(mac_addr=switch_mac)
            mngr_class = dev.get_manager_klass()

            if mngr_class.get_is_use_device_port():
                customer = Customer.objects.get(
                    dev_port__device=dev,
                    dev_port__num=switch_port,
                    device=dev, is_active=True
                )
            else:
                customer = Customer.objects.get(device=dev, is_active=True)
            return customer, dev
        except Customer.DoesNotExist:
            return "User with device with mac '%s' does not exist" % switch_mac
        except Device.DoesNotExist:
            return 'Device with mac %s not found' % switch_mac
        except Port.DoesNotExist:
            return 'Port %(switch_port)d on device with mac %(switch_mac)s does not exist' % {
                'switch_port': int(switch_port),
                'switch_mac': switch_mac
            }
        except MultipleObjectsReturned as e:
            return 'MultipleObjectsReturned:' + ' '.join(
                (type(e), e, str(switch_port))
            )

    def _show_serializer(self):
        serializer = self.get_serializer()
        return Response(serializer.data)

    def _check_data(self, data):
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.data

    @action(methods=('post', 'get'), detail=False)
    def dhcp_request(self, request, *args, **kwargs):
        if request.method == 'GET':
            return self._show_serializer()
        data = self._check_data(request.data)

        opt82 = data.get('opt82')
        remote_id = opt82.get('remote_id')
        circuit_id = opt82.get('circuit_id')
        user_mac = opt82.get('client_mac')

        # попробовать получить мак свича
        if not all([remote_id, circuit_id]):
            return _return_bad_response('Bad option82')
        dev_mac, dev_port = _parse_opt82(remote_id, circuit_id)
        if dev_mac is None:
            return _return_bad_response('Failed to parse option82')

        get_by_op82_res = self.dhcp_get_customer_by_opt82(
            client_ip=None, client_mac=user_mac,
            switch_mac=dev_mac, switch_port=dev_port
        )
        if isinstance(get_by_op82_res, str):
            return _return_bad_response(get_by_op82_res)
        elif isinstance(get_by_op82_res, tuple):
            customer, device = get_by_op82_res
        else:
            return _return_bad_response("Unexpected option82 result type")

        # If customer has an active leases then return latest.
        # If not found then assign new

        ip_lease = CustomerIpLeaseModel.objects.active_leases().order_by('-lease_time').first()
        if ip_lease is None:
            # assign new lease
            # Надо найти подходящие для абона ip пулы
            group_id = customer.group_id
            pools = NetworkIpPool.objects.filter(groups__id__in=[group_id]).iterator()
            free_ip = None
            pool_containts_ip = None
            for pool in pools:
                free_ip = pool.get_free_ip()
                pool_containts_ip = pool
                if not free_ip:
                    continue
            if not free_ip:
                return _return_bad_response("Free ip could not found")
            # Create lease for customer
            db_ip_lease, db_ip_lease_created = CustomerIpLeaseModel.objects.update_or_create(
                ip_address=free_ip,
                pool=pool_containts_ip,
                customer=customer,
                defaults={
                    'mac_address': user_mac,
                    'is_dynamic': True,
                    'lease_time': datetime.now()
                }
            )
        else:
            free_ip = ip_lease.ip_address
            pool_containts_ip = ip_lease.pool

        return {
            "control:Auth-Type": 'Accept',
            "Framed-IP-Address": free_ip,
            # Когда Offer то your ip address заполнен а client ip пустой
            # А когда Inform то наоборот
            # А когда Ack то оба одинаковы
            "DHCP-Your-IP-Address": free_ip,
            "DHCP-Subnet-Mask": '255.255.255.0',
            "DHCP-Router-Address": str(pool_containts_ip.gateway),
            # "DHCP-Domain-Name-Server": '10.12.1.4',
            "DHCP-IP-Address-Lease-Time": DHCP_DEFAULT_LEASE_TIME,
            # "Cleartext-Password": 'dc:0e:a1:66:2e:5d',
        }


class CustomerRadiusAuthViewSet(DjingAuthorizedViewSet):
    queryset = NetworkIpPool.objects.all()
    serializer_class = NetworkIpPoolModelSerializer

    @staticmethod
    def authorize_service(service_name: str):
        return {
            "control:Auth-Type": 'Accept',
            "Cleartext-Password": service_name,
            "Password": service_name,
            "User-Name": service_name,
            "Cisco-AVPair": (
                'subscriber:traffic-class=INTERNET',
                'subscriber:filter-default-action=permit',
                'subscriber:flow-status=enabled'
            )
        }

    def is_access2service(self, username: str, password: str) -> bool:
        return True

    @action(methods=('post',), detail=False)
    def authorize(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if self.is_access2service(username=username, password=password):
            if self.is_allowed_subnet(ip_addr=username):
                return Response({
                    "control:Auth-Type": 'Accept',
                    "User-Name": username,
                    "Session-Timeout": sess_timeout,
                    "Cisco-AVPair": (
                        'subscriber:policer-rate-in=%d' % speed_in,
                        'subscriber:policer-rate-out=%d' % speed_out,
                        # 'subscriber:policer-burst-in=64',
                        # 'subscriber:policer-burst-out=64',
                    ),
                    "Cisco-Account-Info": 'AINTERNET'
                })
            return Response(
                self.authorize_service(service_name=username)
            )
        return Response({
            "control:Auth-Type": 'Reject'
        }, status=status.HTTP_403_FORBIDDEN)

    @action(methods=('post',), detail=False)
    def authenticate(self, request):
        username = request.data.get('username')
        if self.is_access2service(username=username, password=''):
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    @action(methods=('post',), detail=False)
    def accounting(self, request):
        username = request.data.get('username')
        if self.is_access2service(username=username, password=''):
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_401_UNAUTHORIZED)
