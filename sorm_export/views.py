from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.viewsets import DjingModelViewSet
from sorm_export import models
from sorm_export.serializers import model_serializers as serializers


class FiasRecursiveAddressModelViewSet(DjingModelViewSet):
    queryset = models.FiasRecursiveAddressModel.objects.all()
    serializer_class = serializers.FiasRecursiveAddressModelSerializer

    @action(methods=['get'], detail=True)
    def get_parent(self, request, pk=None):
        obj = self.get_object()
        parent = obj.parent_ao
        if not parent:
            return Response()
        serializer = self.get_serializer(obj)
        return Response(serializer.data)
