from typing import Optional
from gateways.gw_facade.base_gw import BaseGateway
from gateways.gw_facade.linux_gw import LinuxGateway
from gateways.gw_facade.mikrotik_gw import MikrotikGateway


class GatewayNetworkError(Exception):
    pass


MIKROTIK = 0
LINUX = 1

GATEWAY_TYPES = ((MIKROTIK, MikrotikGateway), (LINUX, LinuxGateway))


class GatewayFacade(BaseGateway):
    description = "GatewayFacade"

    def __init__(self, gw_type: int, *args, **kwargs):
        self._gw_type = gw_type
        try:
            gw_class = next(klass for num, klass in GATEWAY_TYPES if num == gw_type)
        except StopIteration:
            raise TypeError("gw_type must be GATEWAY_TYPES choice")
        self.gw_instance = gw_class(*args, **kwargs)

    def send_command_add_customer(self, *args, **kwargs) -> Optional[str]:
        return self.gw_instance.send_command_add_customer(*args, **kwargs)

    def send_command_del_customer(self, *args, **kwargs) -> Optional[str]:
        return self.gw_instance.send_command_del_customer(*args, **kwargs)

    def send_command_sync_customer(self, *args, **kwargs) -> Optional[str]:
        return self.gw_instance.send_command_sync_customer(*args, **kwargs)

    def ping_customer(self, *args, **kwargs) -> Optional[str]:
        return self.gw_instance.ping_customer(*args, **kwargs)


__all__ = "GatewayFacade", "GATEWAY_TYPES", "GatewayNetworkError", "MIKROTIK", "LINUX"
