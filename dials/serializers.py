from rest_framework import serializers
from dials.models import ATSDeviceModel, DialLog


class ATSDeviceModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ATSDeviceModel
        fields = '__all__'


class DialLogSerializer(serializers.ModelSerializer):
    # full_filename = serializers.CharField(source='get_dial_full_filename', read_only=True)
    filename = serializers.CharField(source='get_dial_fname', read_only=True)

    class Meta:
        model = DialLog
        fields = '__all__'
