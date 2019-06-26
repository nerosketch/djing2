from rest_framework.serializers import ModelSerializer
from gateways.models import Gateway


class GatewayModelSerializer(ModelSerializer):
    class Meta:
        model = Gateway
        fields = ('pk', 'title', 'ip_address', 'ip_port', 'auth_login',
                  'auth_passw', 'gw_type', 'is_default', 'enabled')
