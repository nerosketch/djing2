from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from rest_framework import status
from easysnmp import EasySNMPTimeoutError
from django_filters.rest_framework import DjangoFilterBackend

from devices.base_intr import DeviceImplementationError
from djing2.viewsets import DjingModelViewSet, DjingListAPIView
from devices.models import Device, Port
from devices import serializers as dev_serializers
from devices.tasks import onu_register
from groupapp.models import Group


def catch_dev_manager_err(fn):
    def wrapper(self, request, pk=None):
        try:
            return fn(self, request, pk)
        except DeviceImplementationError as err:
            return Response({'Error': {
                'text': '%s' % err
            }}, status=status.HTTP_501_NOT_IMPLEMENTED)
        except EasySNMPTimeoutError as err:
            return Response({'Error': {
                'text': err
            }}, status=status.HTTP_408_REQUEST_TIMEOUT)

    # Hack for decorator @action
    wrapper.__name__ = fn.__name__
    return wrapper


class DeviceModelViewSet(DjingModelViewSet):
    queryset = Device.objects.all()
    serializer_class = dev_serializers.DeviceModelSerializer
    filterset_fields = ('group', 'dev_type', 'status', 'is_noticeable')
    filter_backends = (SearchFilter, DjangoFilterBackend)
    search_fields = ('comment', 'ip_address', 'mac_addr')

    def destroy(self, *args, **kwargs):
        r = super().destroy(*args, **kwargs)
        onu_register.delay(
            tuple(dev.pk for dev in Device.objects.exclude(group=None).only('pk').iterator())
        )
        return r

    def create(self, *args, **kwargs):
        r = super().create(*args, **kwargs)
        onu_register.delay(
            tuple(dev.pk for dev in Device.objects.exclude(group=None).only('pk').iterator())
        )
        return r

    @action(detail=True)
    def scan_units_unregistered(self, request, pk=None):
        device = self.get_object()
        manager = device.get_manager_object()
        if hasattr(manager, 'get_fibers'):
            unregistered = map(
                lambda fiber: filter(
                    lambda onu: onu is not None, manager.get_units_unregistered(
                        int(fiber.get('fb_id'))
                    )
                ), manager.get_fibers()
            )
            print(unregistered, list(unregistered))
            return Response(unregistered)
        return Response({'Error': {
            'text': 'Manager has not get_fibers attribute'
        }})

    @action(detail=True)
    @catch_dev_manager_err
    def scan_ports(self, request, pk=None):
        device = self.get_object()
        manager = device.get_manager_object()
        ports = tuple(manager.get_ports())
        if ports is not None and len(ports) > 0 and isinstance(
            ports[0],
            Exception
        ):
            return Response({'Error': {
                'text': '%s' % ports[1]
            }})
        return Response(p.to_dict() for p in ports)

    @action(detail=True)
    @catch_dev_manager_err
    def scan_details(self, request, pk=None):
        device = self.get_object()
        manager = device.get_manager_object()
        data = manager.get_details()
        return Response(data)

    @action(detail=True)
    @catch_dev_manager_err
    def scan_fibers(self, request, pk=None):
        device = self.get_object()
        manager = device.get_manager_object()
        if hasattr(manager, 'get_fibers'):
            fb = manager.get_fibers()
            return Response(fb)
        else:
            return Response({'Error': {
                'text': 'Manager has not get_fibers attribute'
            }})

    @action(detail=True, methods=['get'])
    @catch_dev_manager_err
    def send_reboot(self, request, pk=None):
        device = self.get_object()
        manager = device.get_manager_object()
        manager.reboot(save_before_reboot=False)
        return Response(status=status.HTTP_200_OK)


class DeviceWithoutGroupListAPIView(DjingListAPIView):
    queryset = Device.objects.filter(group=None)
    serializer_class = dev_serializers.DeviceWithoutGroupModelSerializer


class PortModelViewSet(DjingModelViewSet):
    queryset = Port.objects.all()
    serializer_class = dev_serializers.PortModelSerializer


class DeviceGroupsList(DjingListAPIView):
    queryset = Group.objects.all()
    serializer_class = dev_serializers.DeviceGroupsModelSerializer
