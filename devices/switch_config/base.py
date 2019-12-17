from abc import ABC, abstractmethod
from typing import Generator, Optional, Dict, Union, Iterable


from django.utils.translation import gettext_lazy as _

from djing2.lib import RuTimedelta


GeneratorOrTuple = Union[Generator, Iterable]


class DeviceImplementationError(NotImplementedError):
    pass


class DeviceConfigurationError(DeviceImplementationError):
    pass


class DeviceConsoleError(Exception):
    pass


class DevBase(ABC):
    def __init__(self, dev_instance=None):
        self.db_instance = dev_instance

    @property
    def description(self) -> str:
        return 'Base device interface'

    @classmethod
    def get_description(cls):
        return cls.description

    def reboot(self, save_before_reboot=False):
        """
        Send signal reboot to device
        :param save_before_reboot:
        :return: tuple of command return number and text of operation
        """
        return 5, _('Reboot not ready')

    @abstractmethod
    def get_ports(self) -> GeneratorOrTuple:
        """
        If fast operation then just return tuple.
        If long operation then return the generator of ports count first,
        then max chunk size, and ports in next in generations
        """
        raise NotImplementedError

    @abstractmethod
    def port_disable(self, port_num: int):
        """Disable port by number"""
        pass

    @abstractmethod
    def get_device_name(self) -> str:
        """Return device name by snmp"""

    @abstractmethod
    def uptime(self) -> str:
        pass

    @property
    @abstractmethod
    def has_attachable_to_customer(self) -> bool:
        """Can connect device to customer"""

    @property
    @abstractmethod
    def is_use_device_port(self) -> bool:
        """True if used device port while opt82 authorization"""

    @classmethod
    def get_is_use_device_port(cls) -> bool:
        return bool(cls.is_use_device_port)

    @staticmethod
    def validate_extra_snmp_info(v: str) -> None:
        """
        Validate extra snmp field for each device.
        If validation failed then raise en exception from devapp.expect_scripts.ExpectValidationError
        with description of error.
        :param v: String value for validate
        """
        raise NotImplementedError

    @abstractmethod
    def register_device(self, extra_data: Dict):
        pass

    def remove_from_olt(self, extra_data: Dict):
        """Removes device from OLT if devices is ONU"""

    @abstractmethod
    def monitoring_template(self, *args, **kwargs) -> Optional[str]:
        """
        Template for monitoring system config
        :return: string for config file
        """

    def get_details(self) -> dict:
        """
        Return basic information by SNMP or other method
        :return: dict of information
        """
        return {
            'uptime': self.uptime(),
            'name': self.get_device_name(),
            'description': self.description,
            'has_attachable_to_customer': self.has_attachable_to_customer,
            'is_use_device_port': self.is_use_device_port
        }


class BasePort(ABC):

    def __init__(self, num, name, status, mac, speed, uptime=None, snmp_num=None, writable=False):
        self.num = int(num)
        self.snmp_num = int(num) if snmp_num is None else int(snmp_num)
        self.nm = name
        self.st = status
        self._mac = mac
        self.sp = speed
        self.uptime = int(uptime) if uptime else None
        self.writable = writable

    def mac(self) -> str:
        return ':'.join('%x' % ord(i) for i in self._mac) if self._mac else None

    def to_dict(self):
        return {
            'number': self.num,
            'snmp_number': self.snmp_num,
            'name': self.nm,
            'status': self.st,
            'mac_addr': self.mac(),
            'speed': int(self.sp or 0),
            'writable': self.writable,
            'uptime': str(RuTimedelta(seconds=self.uptime / 100)) if self.uptime else None
        }
