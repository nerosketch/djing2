from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from traf_stat.models import TrafficArchiveModel, TrafficCache
from traf_stat.serializers import TrafficCacheModelSerializer, TrafficArchiveModelSerializer
from djing2.viewsets import DjingModelViewSet


class TrafficCacheViewSet(DjingModelViewSet):
    queryset = TrafficCache.objects.all()
    serializer_class = TrafficCacheModelSerializer
    filterset_fields = ['event_time', 'customer']


class TrafficArchiveViewSet(DjingModelViewSet):
    queryset = TrafficArchiveModel.objects.all()
    serializer_class = TrafficArchiveModelSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['event_time', 'customer']
