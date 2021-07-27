from djing2.viewsets import DjingModelViewSet
from maps.models import DotModel
from maps.serializers import DotModelSerializer


class DotModelViewSet(DjingModelViewSet):
    queryset = DotModel.objects.all()
    serializer_class = DotModelSerializer
