from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.viewsets import DjingModelViewSet
from sorm_export import models
from sorm_export.fias_socrbase import AddressFIASInfo
from sorm_export.serializers import model_serializers as serializers


class FiasRecursiveAddressModelViewSet(DjingModelViewSet):
    queryset = models.FiasRecursiveAddressModel.objects.order_by('title')
    serializer_class = serializers.FiasRecursiveAddressModelSerializer

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
        return Response(models.AddressFIASLevelChoices)

    @action(methods=['get'], detail=False)
    def get_ao_types(self, request):
        level = request.query_params.get('level')
        return Response(AddressFIASInfo.get_ao_types(level=level))
