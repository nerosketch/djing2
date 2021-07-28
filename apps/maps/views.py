from rest_framework.decorators import action
from rest_framework.response import Response

from devices.serializers import DeviceModelSerializer
from djing2.viewsets import DjingModelViewSet
from maps.models import DotModel
from maps.serializers import DotModelSerializer


class DotModelViewSet(DjingModelViewSet):
    queryset = DotModel.objects.all()
    serializer_class = DotModelSerializer

    @action(methods=['get'], detail=True)
    def get_devs(self, request, pk=None):
        obj = self.get_object()
        devs = obj.devices.all()
        devs_ser = DeviceModelSerializer(instance=devs, many=True, context={
            'request': request
        })
        return Response(devs_ser.data)
