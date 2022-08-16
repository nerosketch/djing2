from dataclasses import asdict
from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.lib import safe_int
from djing2.viewsets import DjingModelViewSet
from addresses.models import AddressModel, AddressModelTypes
from addresses.serializers import AddressModelSerializer
from addresses.fias_socrbase import AddressFIASInfo


class AddressModelViewSet(DjingModelViewSet):
    queryset = AddressModel.objects.annotate(
        children_count=Count('addressmodel'),
    ).order_by('title')
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
    def get_all_children(self, request):
        # TODO: Make serializer for it
        addr_type = safe_int(request.query_params.get('addr_type'), default=None)
        if not addr_type:
            return Response('addr_type parameter is required', status=status.HTTP_400_BAD_REQUEST)
        parent_addr = safe_int(request.query_params.get('parent_addr'), default=None)
        parent_type = safe_int(request.query_params.get('parent_type'), default=None)
        qs = self.get_queryset()
        qs = qs.filter_from_parent(
            addr_type,
            parent_id=parent_addr,
            parent_type=parent_type
        )
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
        } for val, name in AddressFIASInfo.get_levels())

    @action(methods=['get'], detail=False)
    def get_ao_types(self, request):
        level = safe_int(request.query_params.get('level'), default=None)
        if not level:
            return Response('level parameter required', status=status.HTTP_400_BAD_REQUEST)
        return Response(list(asdict(a) for a in AddressFIASInfo.get_address_types_by_level(level=level)))

    @action(methods=['get'], detail=False)
    def filter_by_fias_level(self, request):
        level = safe_int(request.query_params.get('level'))
        if level and level > 0:
            qs = self.get_queryset()
            qs = qs.filter_by_fias_level(level=level)
            ser = self.serializer_class(instance=qs, many=True, context={
                'request': request
            })
            return Response(ser.data)
        return Response('level parameter required', status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['get'], detail=True)
    def get_full_title(self, request, pk=None):
        full_title = AddressModel.objects.get_address_full_title(
            addr_id=safe_int(pk)
        )
        return Response(full_title)

    @action(methods=['get'], detail=True)
    def get_id_hierarchy(self, request, pk=True):
        obj = self.get_object()
        ids_hierarchy = tuple(i for i in obj.get_id_hierarchy_gen())
        return Response(ids_hierarchy)

    @action(methods=['get'], detail=True)
    def get_address_by_type(self, request, pk=None):
        addr_type = request.query_params.get('addr_type')
        if not addr_type:
            return Response(None)
        addr_type = safe_int(addr_type)
        if not AddressModelTypes.in_range(addr_type):
            return Response('Addr type not in range', status=status.HTTP_400_BAD_REQUEST)
        a = AddressModel.objects.get_address_by_type(addr_id=pk, addr_type=addr_type).first()
        if not a:
            return Response(None)
        ser = self.serializer_class(instance=a)
        return Response(ser.data)
