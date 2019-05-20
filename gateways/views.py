from djing2.viewsets import DjingModelViewSet
from gateways.models import Gateway
from gateways.serializers import GatewayModelSerializer


class GatewayModelViewSet(DjingModelViewSet):
    queryset = Gateway.objects.all()
    serializer_class = GatewayModelSerializer
