from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.lib import safe_int
from djing2.viewsets import DjingModelViewSet
from gateways.models import Gateway
from gateways.serializers import GatewayModelSerializer


class GatewayModelViewSet(DjingModelViewSet):
    queryset = Gateway.objects.all()
    serializer_class = GatewayModelSerializer

    @action(methods=('get',), detail=False)
    def fetch_customers_srvnet_credentials_by_gw(self, request, *args, **kwargs):
        service_id = safe_int(request.query_params.get('gw_id'))
        if service_id > 0:
            ips = Gateway.get_user_credentials_by_ip(gw_id=service_id)
            return Response(ips)
        return Response(status=status.HTTP_403_FORBIDDEN)
