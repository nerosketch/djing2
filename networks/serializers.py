from ipaddress import ip_network

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from networks.models import NetworkModel


class NetworkModelSerializer(serializers.ModelSerializer):
    kind_name = serializers.CharField(source='get_kind_display', read_only=True)

    @staticmethod
    def validate_network(value):
        if value is None:
            raise serializers.ValidationError(_('Network can not be empty'))
        try:
            net = ip_network(value)
            return net.compressed
        except ValueError as e:
            raise serializers.ValidationError(e, code='invalid')

    class Meta:
        model = NetworkModel
        fields = '__all__'
