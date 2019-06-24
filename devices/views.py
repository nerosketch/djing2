from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from djing2.viewsets import DjingModelViewSet, DjingListAPIView
from devices.models import Device, Port
from devices.serializers import DeviceModelSerializer, PortModelSerializer, DeviceGroupsModelSerializer
from groupapp.models import Group


class DeviceModelViewSet(DjingModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceModelSerializer
    filterset_fields = ('group', 'dev_type', 'status', 'is_noticeable')
    filter_backends = (SearchFilter, DjangoFilterBackend)
    search_fields = ('comment', 'ip_address', 'mac_addr')


class PortModelViewSet(DjingModelViewSet):
    queryset = Port.objects.all()
    serializer_class = PortModelSerializer


class DeviceGroupsList(DjingListAPIView):
    queryset = Group.objects.all()
    serializer_class = DeviceGroupsModelSerializer
