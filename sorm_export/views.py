from djing2.viewsets import DjingModelViewSet
from sorm_export import models
from sorm_export.serializers import model_serializers as serializers


class FiasRecursiveAddressModelViewSet(DjingModelViewSet):
    queryset = models.FiasRecursiveAddressModel.objects.all()
    serializer_class = serializers.FiasRecursiveAddressModelSerializer
