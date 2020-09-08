from typing import Iterable

from devices.device_config import DEVICE_TYPES
from devices.device_config.base import DeviceConfigType, BasePON_ONU_Interface, BasePortInterface


def get_all_device_config_types() -> Iterable[DeviceConfigType]:
    all_dtypes = (klass.get_config_types() for code, klass in DEVICE_TYPES if
                  issubclass(klass, (BasePON_ONU_Interface, BasePortInterface)))
    return (a for b in all_dtypes if b for a in b)
