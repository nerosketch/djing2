from rest_framework import serializers
from dials import models


class ATSDeviceModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ATSDeviceModel
        fields = '__all__'


class DialAccountModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DialAccount
        fields = '__all__'


class DialLogSerializer(serializers.ModelSerializer):
    # full_filename = serializers.CharField(source='get_dial_full_filename', read_only=True)
    filename = serializers.CharField(source='get_dial_fname', read_only=True)
    hold_time_human = serializers.CharField(source="hold_time_humanity", read_only=True)
    talk_time_human = serializers.CharField(source="talk_time_humanity", read_only=True)

    class Meta:
        model = models.DialLog
        fields = '__all__'
