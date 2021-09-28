from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.lib import safe_int
from djing2.viewsets import DjingModelViewSet
from addresses.models import AddressModel, AddressModelTypes
from addresses.serializers import AddressModelSerializer


class AddressModelViewSet(DjingModelViewSet):
    queryset = AddressModel.objects.order_by('title')
    serializer_class = AddressModelSerializer
    filterset_fields = ['address_type', 'parent_addr']

    def filter_queryset(self, queryset):
        parent_addr = safe_int(self.request.query_params.get('parent_addr'), default=None)
        if parent_addr == 0:
            return queryset.filter(parent_addr=None)
        return super().filter_queryset(queryset)

    @action(methods=['get'], detail=False)
    def get_addr_types(self, request):
        types = [{'value': value, 'label': label} for value, label in AddressModelTypes.choices]
        return Response(types)

    @action(methods=['get'], detail=False)
    def get_streets(self, request):
        qs = self.get_queryset()
        parent_addr = safe_int(request.query_params.get('parent_addr'), default=None)
        qs = qs.filter_streets(locality_id=parent_addr)
        ser = self.get_serializer(qs, many=True)
        return Response(ser.data)
