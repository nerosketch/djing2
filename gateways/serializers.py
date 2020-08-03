from rest_framework import serializers
from djing2.lib.mixins import BaseCustomModelSerializer
from gateways.models import Gateway


class GatewayModelSerializer(BaseCustomModelSerializer):
    gw_type_str = serializers.CharField(source='get_gw_type_display', read_only=True)
    customers_count = serializers.IntegerField(source='customer_set.count', read_only=True)

    class Meta:
        model = Gateway
        fields = ('id', 'title', 'ip_address', 'ip_port', 'auth_login',
                  'auth_passw', 'gw_type', 'is_default', 'enabled',
                  'gw_type_str', 'customers_count')
