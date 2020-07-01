from typing import Optional
from django.db import models
from gateways.gw_facade.base_gw import BaseGateway
from gateways.gw_facade.linux_gw import LinuxGateway
from gateways.gw_facade.mikrotik_gw import MikrotikGateway


class GatewayNetworkError(Exception):
    pass


class GatewayTypes(models.IntegerChoices):
    MIKROTIK = 0, MikrotikGateway.description
    LINUX = 1, LinuxGateway.description


class GatewayFacade(BaseGateway):
    description = 'GatewayFacade'

    def __init__(self, gw_type: Optional[GatewayTypes, int], *args, **kwargs):
        if isinstance(gw_type, int):
            try:
                gw_type = next(ch for ch in GatewayTypes if ch.value == gw_type)
            except StopIteration:
                raise ValueError('GatewayFacade required GatewayTypes choice in "gw_type" parameter')
        elif isinstance(gw_type, GatewayTypes):
            pass
        else:
            raise TypeError('gw_type must be instance of GatewayTypes or int')
        self._gw_type = gw_type
        gw_map = {
            GatewayTypes.LINUX: LinuxGateway,
            GatewayTypes.MIKROTIK: MikrotikGateway
        }
        gw_class = gw_map.get(gw_type)
        self.gw_instance = gw_class(*args, **kwargs)

    def send_command_add_customer(self, *args, **kwargs) -> Optional[str]:
        return self.gw_instance.send_command_add_customer(*args, **kwargs)

    def send_command_del_customer(self, *args, **kwargs) -> Optional[str]:
        return self.gw_instance.send_command_del_customer(*args, **kwargs)

    def send_command_sync_customer(self, *args, **kwargs) -> Optional[str]:
        return self.gw_instance.send_command_sync_customer(*args, **kwargs)

    def ping_customer(self, *args, **kwargs) -> Optional[str]:
        return self.gw_instance.ping_customer(*args, **kwargs)


__all__ = 'GatewayFacade', 'GatewayTypes', 'GatewayNetworkError'
