from rest_framework.viewsets import ModelViewSet
# from rest_framework.permissions import IsAuthenticated

from gateways.models import Gateway
from gateways.serializers import GatewayModelSerializer


class GatewayModelViewSet(ModelViewSet):
    queryset = Gateway.objects.all()
    # permission_classes = (IsAuthenticated,)
    serializer_class = GatewayModelSerializer
