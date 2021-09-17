from djing2.lib.mixins import BaseCustomModelSerializer
from addresses.models import LocalityModel, StreetModel


class LocalityModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = LocalityModel
        fields = '__all__'


class StreetModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = StreetModel
        fields = '__all__'
