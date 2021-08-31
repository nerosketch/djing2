from rest_framework import serializers
from djing2.lib.mixins import BaseCustomModelSerializer
from gateways.models import Gateway


class GatewayModelSerializer(BaseCustomModelSerializer):
    gw_type_str = serializers.CharField(source="get_gw_type_display", read_only=True)
    customer_count = serializers.IntegerField(read_only=True)
    customer_count_active = serializers.IntegerField(read_only=True)
    customer_count_w_service = serializers.IntegerField(read_only=True)

    class Meta:
        model = Gateway
        fields = '__all__'
