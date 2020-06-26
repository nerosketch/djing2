from enum import Enum
from typing import Optional

from gateways.gw_facade.base_gw import BaseGateway
from gateways.gw_facade.linux_gw import LinuxGateway
from gateways.gw_facade.mikrotik_gw import MikrotikGateway


class GatewayTypes(Enum):
    LINUX = LinuxGateway
    MIKROTIK = MikrotikGateway


class GatewayFacade(BaseGateway):
    description = 'GatewayFacade'

    def __init__(self, gw_type: GatewayTypes, *args, **kwargs):
        self._gw_type = gw_type
        gw_map = {
            GatewayTypes.LINUX: LinuxGateway,
            GatewayTypes.MIKROTIK: MikrotikGateway
        }
        gw_class = gw_map.get(gw_type)
        self.gw_instance = gw_class(*args, **kwargs)

    def send_command_add_customer(self) -> Optional[str]:
        return self.gw_instance.send_command_add_customer()

    def send_command_del_customer(self) -> Optional[str]:
        return self.gw_instance.send_command_del_customer()

    def send_command_sync_customer(self) -> Optional[str]:
        return self.gw_instance.send_command_sync_customer()

    def ping_customer(self) -> Optional[str]:
        return self.gw_instance.ping_customer()


__all__ = 'GatewayFacade', 'GatewayTypes'
