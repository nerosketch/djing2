from djing2.viewsets import DjingModelViewSet
from sorm_export import models
from sorm_export.serializers import model_serializers as serializers


class FIASAddressLevelModelViewSet(DjingModelViewSet):
    queryset = models.FIASAddressLevelModel.objects.all()
    serializer_class = serializers.FIASAddressLevelModelSerializer


class FIASAddressTypeModelViewSet(DjingModelViewSet):
    queryset = models.FIASAddressTypeModel.objects.all()
    serializer_class = serializers.FIASAddressTypeModelSerializer


class FiasCountryModelViewSet(DjingModelViewSet):
    queryset = models.FiasCountryModel.objects.all()
    serializer_class = serializers.FiasCountryModelSerializer


class FiasRegionModelViewSet(DjingModelViewSet):
    queryset = models.FiasRegionModel.objects.all()
    serializer_class = serializers.FiasRegionModelSerializer


class GroupFIASInfoModelViewSet(DjingModelViewSet):
    queryset = models.GroupFIASInfoModel.objects.all()
    serializer_class = serializers.GroupFIASInfoModelSerializer
