from django.db.models.aggregates import Count
from rest_framework.filters import OrderingFilter

from djing2.viewsets import DjingModelViewSet
from services.models import Service, PeriodicPay
from services.serializers import ServiceModelSerializer, PeriodicPayModelSerializer


class ServiceModelViewSet(DjingModelViewSet):
    queryset = Service.objects.annotate(usercount=Count('link_to_service__customer'))
    serializer_class = ServiceModelSerializer
    filterset_fields = ('groups',)
    filter_backends = (OrderingFilter,)
    ordering_fields = ('title', 'speed_in', 'speed_out', 'cost', 'usercount')


class PeriodicPayModelViewSet(DjingModelViewSet):
    queryset = PeriodicPay.objects.all()
    serializer_class = PeriodicPayModelSerializer
