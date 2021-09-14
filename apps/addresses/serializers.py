from rest_framework import serializers
from addresses.models import LocalityModel, StreetModel


class LocalityModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalityModel
        fields = '__all__'


class StreetModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = StreetModel
        field = '__all__'
