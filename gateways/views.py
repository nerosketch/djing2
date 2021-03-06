from django.contrib.messages.api import MessageFailure
from django.db.models import Count, Q
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.lib import safe_int
from djing2.viewsets import DjingModelViewSet
from gateways.models import Gateway
from gateways.serializers import GatewayModelSerializer


class GatewayModelViewSet(DjingModelViewSet):
    queryset = Gateway.objects.annotate(
        customer_count=Count('customer'),
        customer_count_active=Count('customer', filter=Q(customer__is_active=True)),
        customer_count_w_service=Count('customer', filter=Q(customer__is_active=True) & ~Q(customer__current_service=None)),
    )
    serializer_class = GatewayModelSerializer

    @action(detail=False)
    def fetch_customers_srvnet_credentials_by_gw(self, request, *args, **kwargs):
        service_id = safe_int(request.query_params.get('gw_id'))
        if service_id > 0:
            res = Gateway.get_user_credentials_by_gw(gw_id=service_id)
            # res = (customer_id, lease_id, lease_time, lease_mac, ip_address,
            #  speed_in, speed_out, speed_burst, service_start_time,
            #  service_deadline)
            return Response(res)
        return Response(status=status.HTTP_403_FORBIDDEN)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except MessageFailure as msg:
            return Response(str(msg), status=status.HTTP_403_FORBIDDEN)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except MessageFailure as msg:
            return Response(str(msg), status=status.HTTP_403_FORBIDDEN)

    def perform_create(self, serializer, *args, **kwargs):
        return super().perform_create(
            serializer=serializer,
            sites=[self.request.site]
        )
