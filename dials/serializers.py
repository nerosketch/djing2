from rest_framework import serializers
from dials.models import ATSDeviceModel, DialLog


class ATSDeviceModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ATSDeviceModel
        fields = '__all__'


class DialLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DialLog
        fields = '__all__'
