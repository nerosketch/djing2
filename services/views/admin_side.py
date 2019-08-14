from djing2.viewsets import DjingModelViewSet
from services.models import Service, PeriodicPay
from services.serializers import ServiceModelSerializer, PeriodicPayModelSerializer


class ServiceModelViewSet(DjingModelViewSet):
    # queryset = Service.objects.annotate(usercount=Count('linkto_service__abon'))
    queryset = Service.objects.all()
    serializer_class = ServiceModelSerializer
    filterset_fields = ('groups',)


class PeriodicPayModelViewSet(DjingModelViewSet):
    queryset = PeriodicPay.objects.all()
    serializer_class = PeriodicPayModelSerializer
