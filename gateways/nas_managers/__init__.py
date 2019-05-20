from gateways.nas_managers.mod_mikrotik import MikrotikTransmitter
from gateways.nas_managers.core import GatewayNetworkError, GatewayFailedResult
from gateways.nas_managers.structs import SubnetQueue

# Указываем какие реализации шлюзов у нас есть, это будет использоваться в
# web интерфейсе
GW_TYPES = (
    (0, MikrotikTransmitter),
)
