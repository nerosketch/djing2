# from django.db.models import Count
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated

from services.models import Service, PeriodicPay
from services.serializers import ServiceModelSerializer, PeriodicPayModelSerializer


class ServiceModelViewSet(ModelViewSet):
    # queryset = Service.objects.annotate(usercount=Count('linkto_service__abon'))
    queryset = Service.objects.all()
    # permission_classes = (IsAuthenticated,)
    serializer_class = ServiceModelSerializer


class PeriodicPayModelViewSet(ModelViewSet):
    queryset = PeriodicPay.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = PeriodicPayModelSerializer
