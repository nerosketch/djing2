import re
from abc import abstractmethod
from typing import Optional, Tuple, AnyStr
from transliterate import translit
from django.conf import settings
from django.utils.translation import gettext
from devices.device_config.base import Vlans, Macs
from devices.device_config.base_device_strategy import (
    BaseDeviceStrategyContext, BaseDeviceStrategy,
    SNMPWorker, ListDeviceConfigType
)
from djing2.lib import macbin2str, RuTimedelta


class PortType(object):
    __uptime: int
    __mac: bytes
    num: int = 0
    snmp_num: Optional[int] = None
    name: str = ""
    status: bool = False
    speed: int = 0

    def __init__(self, uptime: int = 0, mac: bytes = b'', num=0, snmp_num=None, name='', status=False, speed=0):
        self.uptime = uptime or 0
        self.mac = mac or b''
        self.num = num or 0
        self.snmp_num = int(num or 0) if snmp_num is None else int(snmp_num or 0)
        self.name = name or ''
        self.status = bool(status)
        self.speed = speed or 0

    @property
    def mac(self) -> str:
        m = self.__mac
        if isinstance(m, bytes):
            return macbin2str(m)
        elif isinstance(m, str):
            return m
        raise ValueError('Unexpected type for mac: %s' % type(m))

    @mac.setter
    def mac(self, mac: bytes) -> None:
        self.__mac = mac

    @property
    def uptime(self) -> str:
        if self.__uptime:
            return str(RuTimedelta(seconds=self.__uptime / 100))
        return ''

    @uptime.setter
    def uptime(self, uptime: int) -> None:
        self.__uptime = uptime

    @staticmethod
    def get_config_types() -> ListDeviceConfigType:
        return []

    def as_dict(self) -> dict:
        return {
            'uptime': self.uptime,
            'mac': self.mac,
            'num': self.num,
            'snmp_num': self.snmp_num,
            'name': self.name,
            'status': self.status,
            'speed': self.speed
        }


class SwitchDeviceStrategy(BaseDeviceStrategy):
    ports_len: int

    @staticmethod
    def normalize_name(name: str, vid: Optional[int] = None) -> str:
        if name:
            language_code = getattr(settings, "LANGUAGE_CODE", "ru")
            vname = translit(name, language_code=language_code, reversed=True)
            return re.sub(r"\W+", "_", vname)[:32]
        if vid and isinstance(vid, int):
            return 'v%d' % vid
        return ''

    @abstractmethod
    def get_ports(self) -> tuple:
        """
        If fast operation then just return tuple.
        If long operation then return the generator of ports count first,
        then max chunk size, and ports in next in generations
        """
        raise NotImplementedError

    @abstractmethod
    def port_disable(self, port_num: int) -> None:
        """Disable port by number"""
        raise NotImplementedError

    @abstractmethod
    def port_enable(self, port_num: int):
        raise NotImplementedError

    @abstractmethod
    def read_port_vlan_info(self, port: int) -> Vlans:
        """
        Read info about all vlans on port
        :param port: Port number
        :return: Vlan list
        """
        raise NotImplementedError

    @abstractmethod
    def read_mac_address_port(self, port_num: int) -> Macs:
        """
        Read FDB on port
        :param port_num:
        :return: Mac list
        """
        raise NotImplementedError

    def get_vid_name(self, vid: int) -> str:
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            return snmp.get_item(".1.3.6.1.2.1.17.7.1.4.3.1.1.%d" % vid)

    @abstractmethod
    def read_mac_address_vlan(self, vid: int) -> Macs:
        """
        Read FDB in vlan
        :param vid
        :return: Mac list
        """
        raise NotImplementedError

    def reboot(self, save_before_reboot=False) -> Tuple[int, AnyStr]:
        """
        Send signal reboot to device
        :param save_before_reboot:
        :return: tuple of command return number and text of operation
        """
        return 5, gettext("Reboot not ready")

    @staticmethod
    def validate_extra_snmp_info(v: str) -> None:
        """
        Validate extra snmp field for each device.
        If validation failed then raise en exception from
        devapp.expect_scripts.ExpectValidationError
        with description of error.
        :param v: String value for validate
        """
        raise NotImplementedError


class SwitchDeviceStrategyContext(BaseDeviceStrategyContext):
    _current_dev_manager: SwitchDeviceStrategy

    def get_ports(self) -> tuple:
        """
        If fast operation then just return tuple.
        If long operation then return the generator of ports count first,
        then max chunk size, and ports in next in generations
        """
        return self._current_dev_manager.get_ports()

    def port_disable(self, port_num: int) -> None:
        """Disable port by number"""
        return self._current_dev_manager.port_disable(port_num=port_num)

    def port_enable(self, port_num: int):
        return self._current_dev_manager.port_enable(port_num=port_num)

    def read_port_vlan_info(self, port: int) -> Vlans:
        """
        Read info about all vlans on port
        :param port: Port number
        :return: Vlan list
        """
        return self._current_dev_manager.read_port_vlan_info(port=port)

    def read_mac_address_port(self, port_num: int) -> Macs:
        """
        Read FDB on port
        :param port_num:
        :return: Mac list
        """
        return self._current_dev_manager.read_mac_address_port(port_num=port_num)

    def get_vid_name(self, vid: int) -> str:
        return self._current_dev_manager.get_vid_name(vid=vid)

    def normalize_name(self, name: str, vid: Optional[int] = None) -> str:
        return self._current_dev_manager.normalize_name(name=name, vid=vid)

    def read_mac_address_vlan(self, vid: int) -> Macs:
        """
        Read FDB in vlan
        :param vid
        :return: Mac list
        """
        return self._current_dev_manager.read_mac_address_vlan(vid=vid)

    def reboot(self, save_before_reboot=False) -> Tuple[int, AnyStr]:
        """
        Send signal reboot to device
        :param save_before_reboot:
        :return: tuple of command return number and text of operation
        """
        return self._current_dev_manager.reboot(save_before_reboot=save_before_reboot)

    def validate_extra_snmp_info(self, v: str) -> None:
        """
        Validate extra snmp field for each device.
        If validation failed then raise en exception from
        devapp.expect_scripts.ExpectValidationError
        with description of error.
        :param v: String value for validate
        """
        return self._current_dev_manager.validate_extra_snmp_info(v=v)
