from typing import Optional
from django.utils.translation import gettext_lazy as _
from gateways.gw_facade.base_gw import BaseGateway


class LinuxGateway(BaseGateway):
    description = _('Linux gateway')

    def send_command_add_customer(self, customer_id: int, *args, **kwargs) -> Optional[str]:
        pass

    def send_command_del_customer(self, customer_id: int, *args, **kwargs) -> Optional[str]:
        pass

    def send_command_sync_customer(self, customer_id: int, *args, **kwargs) -> Optional[str]:
        pass

    def ping_customer(self, customer_id: int, *args, **kwargs) -> Optional[str]:
        pass
