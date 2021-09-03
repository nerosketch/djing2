from rest_framework import serializers
from dials import models
from djing2.lib.mixins import BaseCustomModelSerializer


class ATSDeviceModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.ATSDeviceModel
        fields = "__all__"


class DialAccountModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.DialAccount
        fields = "__all__"


class DialLogSerializer(BaseCustomModelSerializer):
    # full_filename = serializers.CharField(source='get_dial_full_filename', read_only=True)
    filename = serializers.CharField(source="get_dial_fname", read_only=True)
    duration_human = serializers.CharField(source="duration_humanity", read_only=True)
    billsec_human = serializers.CharField(source="billsec_humanity", read_only=True)
    call_type_human = serializers.CharField(source="get_call_type_display", read_only=True)

    class Meta:
        model = models.DialLog
        fields = "__all__"
