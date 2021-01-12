from traf_stat.models import TrafficArchiveModel, TrafficCache
from traf_stat.serializers import TrafficCacheModelSerializer, TrafficArchiveModelSerializer
from djing2.viewsets import DjingModelViewSet


class TrafficCacheViewSet(DjingModelViewSet):
    queryset = TrafficCache.objects.all()
    serializer_class = TrafficCacheModelSerializer


class TrafficArchiveViewSet(DjingModelViewSet):
    queryset = TrafficArchiveModel.objects.all()
    serializer_class = TrafficArchiveModelSerializer
    filterset_fields = ['event_time']
