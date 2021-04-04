from typing import Optional

from .base import BaseDeviceInterface, ListDeviceConfigType


class UnknownDevice(BaseDeviceInterface):
    has_attachable_to_customer = False
    description = "Unknown Device"
    is_use_device_port = False

    def get_ports(self) -> tuple:
        return ()

    def get_device_name(self) -> str:
        return "Unknown"

    @staticmethod
    def validate_extra_snmp_info(v: str) -> None:
        pass

    def monitoring_template(self, *args, **kwargs) -> Optional[str]:
        return ""

    @staticmethod
    def get_config_types() -> ListDeviceConfigType:
        return []
