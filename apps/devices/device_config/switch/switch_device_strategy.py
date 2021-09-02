import re
from abc import abstractmethod
from typing import Optional, Tuple, AnyStr
from dataclasses import dataclass
from transliterate import translit
from django.conf import settings
from django.utils.translation import gettext
from django.db.models import Model
from devices.device_config.base import Vlan, Vlans, Macs
from devices.device_config.base_device_strategy import (
    BaseDeviceStrategyContext, BaseDeviceStrategy,
    PortVlanConfigModeChoices, SNMPWorker, ListDeviceConfigType
)
from djing2.lib import macbin2str, RuTimedelta


@dataclass
class PortType:
    model_instance: Model
    num: int = 0
    snmp_num: Optional[int] = None
    name: str = ""
    status: bool = False
    speed: int = 0
    __uptime: int = 0
    __mac: bytes = b""

    def __post_init__(self):
        self.snmp_num = int(self.num) if self.snmp_num is None else int(self.snmp_num)

    @property
    def mac(self) -> str:
        m = self.__mac
        if isinstance(m, bytes):
            return macbin2str(m)
        elif isinstance(m, str):
            return m
        raise ValueError('Unexpected type for mac: %s' % type(m))

    @mac.setter
    def mac(self, mac):
        self.__mac = mac

    @property
    def uptime(self) -> str:
        if self.__uptime:
            return str(RuTimedelta(seconds=self.__uptime / 100))
        return ''

    @uptime.setter
    def uptime(self, time: int):
        self.__uptime = time

    @staticmethod
    def get_config_types() -> ListDeviceConfigType:
        return []


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

    def attach_vlans_to_port(self, vlan_list: Vlans, port_num: int, config_mode: PortVlanConfigModeChoices,
                             request) -> bool:
        """
        Attach vlan set to port
        :param vlan_list:
        :param port_num:
        :param config_mode: devices.serializers.PortVlanConfigModeChoices
        :param request: DRF Request
        :return: Operation result
        """
        raise NotImplementedError

    # @abstractmethod
    # def attach_vlan_to_port(self, vlan: Vlan, port: int, request, tag: bool = True) -> bool:
    #     """
    #     Attach vlan to switch port
    #     :param vlan:
    #     :param port:
    #     :param request: DRF Request
    #     :param tag: Tagged if True or untagged otherwise
    #     :return:
    #     """
    #     _vlan_gen = (v for v in (vlan,))
    #     return self.attach_vlans_to_port(_vlan_gen, port, request)

    def get_vid_name(self, vid: int) -> str:
        dev = self.model_instance
        with SNMPWorker(hostname=dev.ip_address, community=str(dev.man_passw)) as snmp:
            return snmp.get_item(".1.3.6.1.2.1.17.7.1.4.3.1.1.%d" % vid)

    @abstractmethod
    def detach_vlan_from_port(self, vlan: Vlan, port: int, request) -> bool:
        """
        Detach vlan from switch port
        :param vlan:
        :param port:
        :param request: DRF Request
        :return: Operation result
        """
        raise NotImplementedError

    @abstractmethod
    def create_vlans(self, vlan_list: Vlans) -> bool:
        """
        Create new vlan with name
        :param vlan_list:
        :return: Operation result
        """
        raise NotImplementedError

    @abstractmethod
    def delete_vlans(self, vlan_list: Vlans) -> bool:
        """
        Delete vlans from switch
        :param vlan_list:
        :return: Operation result
        """
        raise NotImplementedError

    def create_vlan(self, vlan: Vlan) -> bool:
        _vlan_gen = (v for v in (vlan,))
        return self.create_vlans(_vlan_gen)

    def delete_vlan(self, vid: int, is_management: bool) -> bool:
        _vlan_gen = (v for v in (Vlan(vid=vid, title=None, is_management=is_management, native=False),))
        return self.delete_vlans(_vlan_gen)

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

    @classmethod
    def get_is_use_device_port(cls) -> bool:
        return bool(cls.is_use_device_port)

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

    def attach_vlans_to_port(self, vlan_list: Vlans, port_num: int, config_mode: PortVlanConfigModeChoices,
                             request) -> bool:
        """
        Attach vlan set to port
        :param vlan_list:
        :param port_num:
        :param config_mode: devices.serializers.PortVlanConfigModeChoices
        :param request: DRF Request
        :return: Operation result
        """
        return self._current_dev_manager.attach_vlans_to_port(vlan_list=vlan_list, port_num=port_num,
                                                              config_mode=config_mode, request=request)

    # @abstractmethod
    # def attach_vlan_to_port(self, vlan: Vlan, port: int, request, tag: bool = True) -> bool:
    #     """
    #     Attach vlan to switch port
    #     :param vlan:
    #     :param port:
    #     :param request: DRF Request
    #     :param tag: Tagged if True or untagged otherwise
    #     :return:
    #     """
    #     _vlan_gen = (v for v in (vlan,))
    #     return self.attach_vlans_to_port(_vlan_gen, port, request)

    def get_vid_name(self, vid: int) -> str:
        return self._current_dev_manager.get_vid_name(vid=vid)

    def detach_vlan_from_port(self, vlan: Vlan, port: int, request) -> bool:
        """
        Detach vlan from switch port
        :param vlan:
        :param port:
        :param request: DRF Request
        :return: Operation result
        """
        return self._current_dev_manager.detach_vlan_from_port(vlan=vlan, port=port, request=request)

    def normalize_name(self, name: str, vid: Optional[int] = None) -> str:
        return self._current_dev_manager.normalize_name(name=name, vid=vid)

    @abstractmethod
    def create_vlans(self, vlan_list: Vlans) -> bool:
        """
        Create new vlan with name
        :param vlan_list:
        :return: Operation result
        """
        return self._current_dev_manager.create_vlans(vlan_list=vlan_list)

    @abstractmethod
    def delete_vlans(self, vlan_list: Vlans) -> bool:
        """
        Delete vlans from switch
        :param vlan_list:
        :return: Operation result
        """
        return self._current_dev_manager.delete_vlans(vlan_list=vlan_list)

    def create_vlan(self, vlan: Vlan) -> bool:
        return self._current_dev_manager.create_vlan(vlan=vlan)

    def delete_vlan(self, vid: int, is_management: bool) -> bool:
        return self._current_dev_manager.delete_vlan(vid=vid, is_management=is_management)

    @abstractmethod
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
