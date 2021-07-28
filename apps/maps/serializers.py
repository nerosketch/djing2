from rest_framework import serializers

from devices.models import Device
from djing2.lib.mixins import BaseCustomModelSerializer
from maps.models import DotModel


class DotModelSerializer(BaseCustomModelSerializer):
    devices = serializers.PrimaryKeyRelatedField(
        many=True,
        allow_empty=True,
        queryset=Device.objects.all()
    )

    class Meta:
        model = DotModel
        fields = '__all__'
