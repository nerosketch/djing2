import re
from enum import IntEnum
from devices.device_config.base import Vlan, Vlans, DeviceImplementationError
from devices.device_config.base_device_strategy import BaseDeviceStrategy, global_device_types_map, DeviceConfigType
from devices.device_config.pon.pon_device_strategy import PonOnuDeviceStrategy
from devices.device_config.switch.switch_device_strategy import SwitchDeviceStrategy


class UnknownDevice(BaseDeviceStrategy):
    has_attachable_to_customer = False
    description = "Unknown Device"
    is_use_device_port = False

    def get_device_name(self) -> str:
        return "Unknown"

    @staticmethod
    def validate_extra_snmp_info(v: str) -> None:
        pass

    def get_uptime(self) -> str:
        return '0'

    def read_all_vlan_info(self) -> Vlans:
        yield Vlan(vid=1, title='Default')


DEVICE_TYPE_UNKNOWN = 0

DEVICE_TYPES = [(uniq_num, dev_klass) for uniq_num, dev_klass in global_device_types_map.items()]
DEVICE_TYPES.insert(0, (DEVICE_TYPE_UNKNOWN, UnknownDevice))

DEVICE_ONU_TYPES = [dev_klass for uniq_num, dev_klass in DEVICE_TYPES if issubclass(
    dev_klass, PonOnuDeviceStrategy)]

DEVICE_SWITCH_TYPES = [dev_klass for uniq_num, dev_klass in DEVICE_TYPES if issubclass(
    dev_klass, SwitchDeviceStrategy)]


DeviceTypeEnum = IntEnum('DeviceTypeEnum', {
    dev_klass.__name__: uniq_num for uniq_num, dev_klass in global_device_types_map.items()
})

# TODO: Check it
# Check type for device config classes
def _check_device_config_types():
    allowed_symbols_pattern = re.compile(r"^\w{1,64}$")
    all_dtypes = (
        klass.get_config_types()
        for code, klass in DEVICE_TYPES
        if issubclass(klass, PonOnuDeviceStrategy)
    )
    all_dtypes = (a for b in all_dtypes if b for a in b)
    for dtype in all_dtypes:
        if not issubclass(dtype, DeviceConfigType):
            raise DeviceImplementationError(
                'device config type "%s" must be subclass of DeviceConfigType' % repr(dtype)
            )
        device_config_short_code = str(dtype.short_code)
        if not allowed_symbols_pattern.match(device_config_short_code):
            raise DeviceImplementationError(
                r'device config "%s" short_code must be equal regexp "^\w{1,64}$"' % repr(dtype)
            )


_check_device_config_types()
