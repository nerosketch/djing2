from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.viewsets import DjingModelViewSet
from addresses.models import AddressModel, AddressModelTypes
from addresses.serializers import AddressModelSerializer


class AddressModelViewSet(DjingModelViewSet):
    queryset = AddressModel.objects.order_by('title')
    serializer_class = AddressModelSerializer
    filterset_fields = ['address_type']

    @action(methods=['get'], detail=False)
    def get_addr_types(self, request):
        types = [{'value': value, 'label': label} for value, label in AddressModelTypes.choices]
        return Response(types)
