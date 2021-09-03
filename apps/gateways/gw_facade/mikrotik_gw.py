from typing import Optional
from django.utils.translation import gettext_lazy as _
from gateways.gw_facade.base_gw import BaseGateway


class MikrotikGateway(BaseGateway):
    description = _("Mikrotik gateway")

    def send_command_add_customer(self, *args, **kwargs) -> Optional[str]:
        pass

    def send_command_del_customer(self, *args, **kwargs) -> Optional[str]:
        pass

    def send_command_sync_customer(self, *args, **kwargs) -> Optional[str]:
        pass

    def ping_customer(self, *args, **kwargs) -> Optional[str]:
        pass
