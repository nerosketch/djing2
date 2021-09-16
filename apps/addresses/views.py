from djing2.viewsets import DjingModelViewSet
from addresses.models import LocalityModel, StreetModel
from addresses.serializers import LocalityModelSerializer, StreetModelSerializer


class LocalityModelViewSet(DjingModelViewSet):
    queryset = LocalityModel.objects.order_by('title')
    serializer_class = LocalityModelSerializer


class StreetModelViewSet(DjingModelViewSet):
    queryset = StreetModel.objects.order_by('name')
    serializer_class = StreetModelSerializer
    filterset_fields = ['locality']
