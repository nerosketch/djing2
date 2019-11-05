from django.db.models.aggregates import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from customers.models import Customer
from djing2.viewsets import DjingModelViewSet
from services.models import Service, PeriodicPay, OneShotPay
from services.serializers import (
    ServiceModelSerializer,
    PeriodicPayModelSerializer,
    OneShotPaySerializer
)


class ServiceModelViewSet(DjingModelViewSet):
    queryset = Service.objects.annotate(usercount=Count('link_to_service__customer'))
    serializer_class = ServiceModelSerializer
    filterset_fields = ('groups',)
    filter_backends = (DjangoFilterBackend, OrderingFilter,)
    ordering_fields = ('title', 'speed_in', 'speed_out', 'cost', 'usercount')

    @action(methods=('get',), detail=True)
    def users(self, request, pk=None):
        qs = Customer.objects.filter(
            current_service__service__id=pk
        ).select_related('group').values(
            'id', 'group_id', 'username', 'fio'
        )
        return Response(qs)


class PeriodicPayModelViewSet(DjingModelViewSet):
    queryset = PeriodicPay.objects.all()
    serializer_class = PeriodicPayModelSerializer


class OneShotModelViewSet(DjingModelViewSet):
    queryset = OneShotPay.objects.all()
    serializer_class = OneShotPaySerializer
