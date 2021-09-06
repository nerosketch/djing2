from dynamicfields.models import FieldModel
from dynamicfields.serializers import FieldModelSerializer
from djing2.viewsets import DjingModelViewSet


class FieldModelViewSet(DjingModelViewSet):
    queryset = FieldModel.objects.all()
    serializer_class = FieldModelSerializer
