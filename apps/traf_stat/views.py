from datetime import datetime

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from djing2.lib import safe_int, safe_float
from traf_stat.models import TrafficArchiveModel, TrafficCache
from traf_stat.serializers import TrafficCacheModelSerializer, TrafficArchiveModelSerializer
from djing2.viewsets import DjingModelViewSet


class TrafficCacheViewSet(DjingModelViewSet):
    queryset = TrafficCache.objects.all()
    serializer_class = TrafficCacheModelSerializer
    filterset_fields = ["event_time", "customer"]


class TrafficArchiveViewSet(DjingModelViewSet):
    queryset = TrafficArchiveModel.objects.all()
    serializer_class = TrafficArchiveModelSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["event_time", "customer"]

    @action(methods=["get"], detail=False)
    def get_chart_data(self, request):
        customer_id = safe_int(request.query_params.get("customer_id"))
        start_time = safe_float(request.query_params.get("start_time"))
        end_date = safe_float(request.query_params.get("end_date"))
        if 0 in [customer_id, start_time]:
            return Response("customer_id and start_date is required", status=status.HTTP_403_FORBIDDEN)
        if end_date <= 0:
            end_date = None
        customer_id = customer_id if customer_id > 0 else 0
        start_date = start_time if start_time > 0 else 0
        charts = TrafficArchiveModel.objects.get_chart_data(
            customer_id=customer_id,
            start_date=datetime.fromtimestamp(start_date),
            end_date=datetime.fromtimestamp(end_date) if end_date else None,
        )
        return Response(charts)
