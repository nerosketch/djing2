from django.db.models.expressions import RawSQL, Q
from django.db.models.aggregates import Count
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from djing2.lib import safe_int
from djing2.viewsets import DjingModelViewSet
from addresses.models import AddressModel, AddressModelTypes, AddressFIASLevelChoices
from addresses.serializers import AddressModelSerializer, AddressAutocompleteSearchResultSerializer
from addresses.fias_socrbase import AddressFIASInfo


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
        return Response(AddressFIASLevelChoices)

    @action(methods=['get'], detail=False)
    def get_ao_types(self, request):
        level = request.query_params.get('level')
        return Response(AddressFIASInfo.get_ao_types(level=level))


class AddressAutocompleteAPIView(APIView):
    """Address autocomplete endpoint"""
    # http_method_names = ['get', 'post', 'options']
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = AddressAutocompleteSearchResultSerializer
    limit_size = 5

    @classmethod
    def get_queryset(cls):
        return AddressModel.objects.all()

    def get(self, request, *args, **kwargs):
        search_string = request.query_params.get('search')
        if not search_string:
            all_addrs = self.get_all(request)
            return self.return_results(
                queryset=all_addrs
            )
        filtered_results = self.filter_search(search_string)
        return self.return_results(
            queryset=filtered_results
        )

    def return_results(self, queryset, many=True):
        limited_queryset = queryset[:self.limit_size]
        ser = self.serializer_class(instance=limited_queryset, many=many, context={'request': self.request})
        return Response(ser.data)

    def get_all(self, request):
        return self.get_queryset()

    def filter_search(self, search_string: str):
        qs = self.get_queryset()

        chanked_search_string = search_string.split(' ')
        print(chanked_search_string)
        step_1_qs_addrs = qs.filter(title__in__icontains=chanked_search_string)

        step2 = step_1_qs_addrs.annotate(
            adrcount=Count('id', filter=Q(title__icontains=search_string))
        )
        print(step2.query)
        for r in step2:
            sr = self.serializer_class(instance=r)
            print(sr.data)

        # query_raw_sql = RawSQL(
        #     sql=(
        #         "WITH RECURSIVE chain(id, parent_addr_id) AS ("
        #         "SELECT id, parent_addr_id "
        #         "FROM addresses "
        #         "WHERE id = %s "
        #         "UNION "
        #         "SELECT a.id, a.parent_addr_id "
        #         "FROM chain c "
        #         "LEFT JOIN addresses a ON a.parent_addr_id = c.id"
        #         ")"
        #         "SELECT id FROM chain WHERE id IS NOT NULL"
        #     ),
        #     params=[12]
        # )

        return step2
