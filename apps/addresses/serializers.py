from rest_framework import serializers
from addresses.models import LocalityModel, StreetModel


class LocalityModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocalityModel
        exclude = ['sites']


class StreetModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = StreetModel
        fields = '__all__'
