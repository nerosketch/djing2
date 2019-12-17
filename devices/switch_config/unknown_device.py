from typing import Optional

from devices.switch_config.base import GeneratorOrTuple
from .base import DevBase


class UnknownDevice(DevBase):
    has_attachable_to_customer = False
    description = 'Unknown Device'
    is_use_device_port = False

    def get_ports(self) -> GeneratorOrTuple:
        return ()

    def get_device_name(self) -> str:
        return 'Unknown'

    @staticmethod
    def validate_extra_snmp_info(v: str) -> None:
        pass

    def monitoring_template(self, *args, **kwargs) -> Optional[str]:
        return ''
