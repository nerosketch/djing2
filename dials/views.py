from djing2.viewsets import DjingModelViewSet
from dials import serializers, models


class ATSDeviceModelViewSet(DjingModelViewSet):
    queryset = models.ATSDeviceModel.objects.all()
    serializer_class = serializers.ATSDeviceModelSerializer


class DialLogModelViewSet(DjingModelViewSet):
    queryset = models.DialLog.objects.all()
    serializer_class = serializers.DialLogSerializer
