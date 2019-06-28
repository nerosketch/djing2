from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from djing2.viewsets import DjingModelViewSet, DjingListAPIView
from devices.models import Device, Port
from devices import serializers as dev_serializers
from groupapp.models import Group


class DeviceModelViewSet(DjingModelViewSet):
    queryset = Device.objects.all()
    serializer_class = dev_serializers.DeviceModelSerializer
    filterset_fields = ('group', 'dev_type', 'status', 'is_noticeable')
    filter_backends = (SearchFilter, DjangoFilterBackend)
    search_fields = ('comment', 'ip_address', 'mac_addr')


class DeviceWithoutGroupListAPIView(DjingListAPIView):
    queryset = Device.objects.filter(group=None)
    serializer_class = dev_serializers.DeviceWithoutGroupModelSerializer


class PortModelViewSet(DjingModelViewSet):
    queryset = Port.objects.all()
    serializer_class = dev_serializers.PortModelSerializer


class DeviceGroupsList(DjingListAPIView):
    queryset = Group.objects.all()
    serializer_class = dev_serializers.DeviceGroupsModelSerializer
