from django.db.models.aggregates import Count
from django_filters.rest_framework import DjangoFilterBackend
from guardian.shortcuts import get_objects_for_user
from rest_framework.filters import OrderingFilter

from djing2.lib.filters import CustomObjectPermissionsFilter
from djing2.viewsets import DjingModelViewSet
from groupapp.models import Group
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
    filter_backends = (CustomObjectPermissionsFilter, DjangoFilterBackend, OrderingFilter,)
    ordering_fields = ('title', 'speed_in', 'speed_out', 'cost', 'usercount')

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        # TODO: May optimize
        grps = get_objects_for_user(
            user=self.request.user,
            perms='groupapp.view_group',
            klass=Group
        )
        return qs.filter(groups__in=grps)


class PeriodicPayModelViewSet(DjingModelViewSet):
    queryset = PeriodicPay.objects.all()
    serializer_class = PeriodicPayModelSerializer


class OneShotModelViewSet(DjingModelViewSet):
    queryset = OneShotPay.objects.all()
    serializer_class = OneShotPaySerializer
