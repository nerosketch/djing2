from djing2.viewsets import DjingModelViewSet
from devices.models import Device, Port
from devices.serializers import DeviceModelSerializer, PortModelSerializer


class DeviceModelViewSet(DjingModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceModelSerializer
    filterset_fields = ('group', 'dev_type', 'status', 'is_noticeable')


class PortModelViewSet(DjingModelViewSet):
    queryset = Port.objects.all()
    serializer_class = PortModelSerializer
