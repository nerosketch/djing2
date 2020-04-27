from ipaddress import ip_address

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

    @action(methods=('get', 'post'), detail=False)
    def get_service(self, request):
        if request.method == 'GET':
            serializer = self.get_serializer()
            return Response(serializer.data)
        data = self._check_data(request.data)

        customer_ip = data.get('customer_ip')
        # password = data.get('password')

        customer_service = CustomerService.get_user_credentials_by_ip(
            ip_addr=customer_ip
        )
        if customer_service is None:
            return Response('Customer service not found', status=status.HTTP_404_NOT_FOUND)

        sess_time = customer_service.calc_session_time()
        return Response({
            'ip': customer_ip,
            'session_time': int(sess_time.total_seconds()),
            'speed_in': customer_service.service.speed_in,
            'speed_out': customer_service.service.speed_out
        })

    @action(methods=('get',), detail=False)
    def get_access(self, request):
        user_ip = request.query_params.get('user_ip')
        if not user_ip:
            return Response('user_ip parameter is required', status=status.HTTP_403_FORBIDDEN)
        try:
            user_ip = str(ip_address(user_ip))
            is_access = CustomerService.get_service_permit_by_ip(ip_addr=user_ip)
            ret_status = status.HTTP_200_OK if is_access else status.HTTP_403_FORBIDDEN
            return Response(is_access, status=ret_status)
        except ValueError as err:
            return Response(str(err), status=status.HTTP_400_BAD_REQUEST)
