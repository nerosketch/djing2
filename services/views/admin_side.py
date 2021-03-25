from django.db.models.aggregates import Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from djing2.lib.filters import CustomObjectPermissionsFilter
from djing2.lib.mixins import SitesFilterMixin
from djing2.viewsets import DjingModelViewSet
from profiles.models import UserProfileLogActionType
from services.models import Service, PeriodicPay, OneShotPay
from services.serializers import (
    ServiceModelSerializer,
    PeriodicPayModelSerializer,
    OneShotPaySerializer
)


class ServiceModelViewSet(SitesFilterMixin, DjingModelViewSet):
    queryset = Service.objects.annotate(usercount=Count('link_to_service'))
    serializer_class = ServiceModelSerializer
    filterset_fields = ('groups',)
    filter_backends = (CustomObjectPermissionsFilter, DjangoFilterBackend, OrderingFilter,)
    ordering_fields = ('title', 'speed_in', 'speed_out', 'cost', 'usercount')

    def perform_create(self, serializer, *args, **kwargs):
        service = super().perform_create(
            serializer=serializer,
            sites=[self.request.site]
        )
        if service is not None:
            self.request.user.log(
                do_type=UserProfileLogActionType.CREATE_SERVICE,
                additional_text='"%(title)s", "%(descr)s", %(amount).2f' % {
                    'title': service.title or '-',
                    'descr': service.descr or '-',
                    'amount': service.cost or 0.0
                })
        return service

    def perform_destroy(self, instance):
        self.request.user.log(
            do_type=UserProfileLogActionType.DELETE_SERVICE,
            additional_text='"%(title)s", "%(descr)s", %(amount).2f' % {
                'title': instance.title or '-',
                'descr': instance.descr or '-',
                'amount': instance.cost or 0.0
            })
        return super().perform_destroy(instance)


class PeriodicPayModelViewSet(SitesFilterMixin, DjingModelViewSet):
    queryset = PeriodicPay.objects.all()
    serializer_class = PeriodicPayModelSerializer

    def perform_create(self, serializer, *args, **kwargs):
        return super().perform_create(
            serializer=serializer,
            sites=[self.request.site]
        )


class OneShotModelViewSet(SitesFilterMixin, DjingModelViewSet):
    queryset = OneShotPay.objects.all()
    serializer_class = OneShotPaySerializer

    def perform_create(self, serializer, *args, **kwargs):
        return super().perform_create(
            serializer=serializer,
            sites=[self.request.site]
        )
