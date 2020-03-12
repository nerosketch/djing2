from django.core.exceptions import MultipleObjectsReturned
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.lib import safe_int
from djing2.viewsets import DjingAuthorizedViewSet
from customers.models.customer import Customer
from devices.models import Device, Port


class RadiusDHCPMixin(object):
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
            return customer
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

    @staticmethod
    def unknown_auth_action(*args, **kwargs):
        """
        Вызывается когда RADIUS в параметре 'auth_action'
        передал имя метода, который тут не реализован
        """
        return {
            "control:Auth-Type": 'Reject',
        }, status.HTTP_403_FORBIDDEN

    def dhcp_request(self, request):
        opt82 = request.data.get('opt82')
        if not opt82:
            return
        remote_id = opt82.get('remote-id')
        circuit_id = opt82.get('circuit-id')

        # попробовать получить мак свича
        dev_mac = remote_id
        dev_port = safe_int(circuit_id)
        customer = self.dhcp_get_customer_by_opt82(
            client_ip=None, client_mac=None,
            switch_mac=dev_mac, switch_port=dev_port
        )

        #
        # Тут надо по данным из radius получать мак и порт свича
        # чтоб по ним находить абонента и давать ему ip
        #
        if not all([remote_id, circuit_id]):
            return
        return {
            "control:Auth-Type": 'Accept',
            "Framed-IP-Address": ip,
            "DHCP-Your-IP-Address": ip,
            "DHCP-Subnet-Mask": '255.255.255.0',
            "DHCP-Router-Address": '10.12.5.1',
            "DHCP-Domain-Name-Server": '10.12.1.4',
            "DHCP-IP-Address-Lease-Time": 3600,
            "Cleartext-Password": 'dc:0e:a1:66:2e:5d',
        }


class CustomerRadiusAuthViewSet(RadiusDHCPMixin, DjingAuthorizedViewSet):
    default_session_time = 3600
    queryset = Customer.objects.all()

    def authorize_service(self, service_name: str):
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
    def post_auth(self, request):
        # Через радиус передаём какое именно действие нам надо выполнить.
        # Если указанное действие не найдено среди реализованных методов то
        # вызываем unknown_auth_action(request, request.data)
        # В случае запроса ip адреса через DHCP значение будет dhcp_request,
        # это указывается в конфиге freeradius
        auth_action_param = request.data.get('auth_action')
        auth_action = getattr(self, auth_action_param, 'unknown_auth_action')
        if callable(auth_action):
            auth_result = auth_action(request, request.data)
            if auth_result:
                return Response(auth_result)
        return Response(status=status.HTTP_401_UNAUTHORIZED)

    @action(methods=('post',), detail=False)
    def accounting(self, request):
        username = request.data.get('username')
        if self.is_access2service(username=username, password=''):
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_401_UNAUTHORIZED)
