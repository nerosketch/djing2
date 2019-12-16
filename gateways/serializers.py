from djing2.lib.mixins import BaseCustomModelSerializer
from gateways.models import Gateway


class GatewayModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = Gateway
        fields = ('pk', 'title', 'ip_address', 'ip_port', 'auth_login',
                  'auth_passw', 'gw_type', 'is_default', 'enabled')
