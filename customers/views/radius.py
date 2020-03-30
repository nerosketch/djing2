from datetime import timedelta

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from customers.models import CustomerService
from customers.serializers import RadiusCustomerServiceRequestSerializer
from djing2.viewsets import DjingAuthorizedViewSet


class RadiusCustomerServiceRequestViewSet(DjingAuthorizedViewSet):
    serializer_class = RadiusCustomerServiceRequestSerializer

    def _check_data(self, data):
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.serializer = serializer
        return serializer.data

    @staticmethod
    def authorize_service_type(service_name: str) -> dict:
        # TODO: move this to freeradius config
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

    @staticmethod
    def authorize_service_credentials(username: str, session_time: timedelta,
                                      speed_in: float, speed_out: float) -> dict:
        """
        Return RADIUS AV pairs for customer speed credentials
        :param username: customers ip_address or mac_address from BRAS
        :param session_time: remaining time to work
        :param speed_in: inbound speed limit for customer session
        :param speed_out: outbound speed limit for customer session
        :return: Dict of radius av pairs
        """
        sess_time_secs = session_time.total_seconds()
        return {
            "control:Auth-Type": 'Accept',
            "User-Name": username,
            "Session-Timeout": sess_time_secs,
            "Idle-Timeout": sess_time_secs,
            "Cisco-AVPair": (
                'subscriber:policer-rate-in=%d' % speed_in * 1024,
                'subscriber:policer-rate-out=%d' % speed_out * 1024,
                'subscriber:policer-burst-in=188',
                'subscriber:policer-burst-out=188',
            ),
            "Cisco-Account-Info": 'AINTERNET'
        }

    @action(methods=('get', 'post'), detail=False)
    def get_service(self, request, *args, **kwargs):
        if request.method == 'GET':
            serializer = self.get_serializer()
            return Response(serializer.data)
        data = self._check_data(request.data)

        # Ip address got Through username
        username = data.get('username')
        # password = data.get('password')

        if username == 'INTERNET':
            return Response(self.authorize_service_type(service_name=username))

        customer_service = CustomerService.get_user_credentials_by_ip(
            ip_addr=username
        )
        if customer_service is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        return Response(self.authorize_service_credentials(
            username=username,
            session_time=customer_service.calc_session_time(),
            speed_in=customer_service.service.speed_in,
            speed_out=customer_service.service.speed_out
        ))
