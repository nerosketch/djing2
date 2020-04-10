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
    def get_service(self, request, *args, **kwargs):
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
            'session_time': sess_time.total_seconds(),
            'speed_in': customer_service.service.speed_in,
            'speed_out': customer_service.service.speed_out
        })
