from rest_framework import serializers
from sorm_export import models


class FIASAddressLevelModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FIASAddressLevelModel
        fields = '__all__'


class FIASAddressTypeModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FIASAddressTypeModel
        fields = '__all__'


class FiasCountryModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FiasCountryModel
        fields = '__all__'


class FiasRegionModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FiasRegionModel
        fields = '__all__'


class GroupFIASInfoModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.GroupFIASInfoModel
        fields = '__all__'
