from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.lib import safe_int
from djing2.viewsets import DjingModelViewSet
from sorm_export import models
from sorm_export.fias_socrbase import AddressFIASLevelChoices, AddressFIASInfo
from sorm_export.serializers import model_serializers as serializers


class FiasRecursiveAddressModelViewSet(DjingModelViewSet):
    queryset = models.FiasRecursiveAddressModel.objects.all()
    serializer_class = serializers.FiasRecursiveAddressModelSerializer
    ordering_fields = ['title']

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
        if level is not None:
            level = safe_int(level)
            ao_type_info = {ao_level: ao_info for ao_level, ao_info in AddressFIASInfo.items() if ao_level == level}
        else:
            ao_type_info = AddressFIASInfo

        ao_type_choices = ((num, '%s %s' % name) for lev, inf in ao_type_info.items() for num, name in inf.items())
        return Response(ao_type_choices)
