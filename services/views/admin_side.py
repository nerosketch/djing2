from django.db.models.aggregates import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from djing2.lib.filters import CustomObjectPermissionsFilter
from djing2.lib.mixins import SitesGroupFilterMixin, SitesFilterMixin
from djing2.viewsets import DjingModelViewSet
from services.models import Service, PeriodicPay, OneShotPay
from services.serializers import (
    ServiceModelSerializer,
    PeriodicPayModelSerializer,
    OneShotPaySerializer
)


class ServiceModelViewSet(SitesGroupFilterMixin, DjingModelViewSet):
    queryset = Service.objects.annotate(usercount=Count('link_to_service__customer'))
    serializer_class = ServiceModelSerializer
    filterset_fields = ('groups',)
    filter_backends = (CustomObjectPermissionsFilter, DjangoFilterBackend, OrderingFilter,)
    ordering_fields = ('title', 'speed_in', 'speed_out', 'cost', 'usercount')


class PeriodicPayModelViewSet(SitesFilterMixin, DjingModelViewSet):
    queryset = PeriodicPay.objects.all()
    serializer_class = PeriodicPayModelSerializer


class OneShotModelViewSet(SitesFilterMixin, DjingModelViewSet):
    queryset = OneShotPay.objects.all()
    serializer_class = OneShotPaySerializer
