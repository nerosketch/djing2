from dataclasses import asdict
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.lib import safe_int
from djing2.viewsets import DjingModelViewSet
from addresses.models import AddressModel, AddressModelTypes, AddressFIASLevelChoices
from addresses.serializers import AddressModelSerializer
from addresses.fias_socrbase import AddressFIASInfo


class AddressModelViewSet(DjingModelViewSet):
    queryset = AddressModel.objects.order_by('title')
    serializer_class = AddressModelSerializer
    filterset_fields = ['address_type', 'parent_addr', 'fias_address_type']

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

    @action(methods=['get'], detail=True)
    def get_parent(self, request, pk=None):
        obj = self.get_object()
        parent = obj.parent_ao
        if not parent:
            return Response()
        serializer = self.get_serializer(obj)
        return Response(serializer.data)

    @action(methods=['get'], detail=False)
    def get_ao_levels(self, request):
        return Response({
            'name': name,
            'value': val
        } for val, name in AddressFIASLevelChoices)

    @action(methods=['get'], detail=False)
    def get_ao_types(self, request):
        level = safe_int(request.query_params.get('level'), default=None)
        if not level:
            return Response('level parameter required', status=status.HTTP_400_BAD_REQUEST)
        return Response(list(asdict(a) for a in AddressFIASInfo.get_address_types_by_level(level=level)))
