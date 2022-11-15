from dataclasses import dataclass
from typing import Generator, Optional, Iterable
from abc import abstractmethod

from devices.device_config.base import UnsupportedReadingVlan
from devices.device_config.base_device_strategy import (
    BaseDeviceStrategyContext, ListDeviceConfigType,
    BaseDeviceStrategy
)
from djing2.lib import macbin2str


@dataclass
class FiberDataClass:
    fb_id: int
    fb_name: str
    fb_onu_num: int


class PonOltDeviceStrategy(BaseDeviceStrategy):
    # @abstractmethod
    # def attach_vlans_to_uplink(self, vlans: Vlans, *args, **kwargs) -> bool:
    #     """
    #     Attach vlan to uplink port
    #     :param vlans: vlan iterable, each element must be instance of Vlan
    #     :param args: optional parameters for each implementation
    #     :param kwargs: optional parameters for each implementation
    #     :return: nothing
    #     """
    #     raise NotImplementedError

    @abstractmethod
    def scan_onu_list(self) -> Generator:
        raise NotImplementedError

    @abstractmethod
    def get_fibers(self) -> Generator[FiberDataClass, None, None]:
        raise NotImplementedError

    def get_units_unregistered(self, *args, **kwargs) -> Iterable:
        return ()

    def get_ports_on_fiber(self, fiber_num: int) -> Iterable:
        return ()


class PonOLTDeviceStrategyContext(BaseDeviceStrategyContext):
    _current_dev_manager: PonOltDeviceStrategy
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)

    # @abstractmethod
    # def attach_vlans_to_uplink(self, vlans: Vlans, *args, **kwargs) -> bool:
    #     """
    #     Attach vlan to uplink port
    #     :param vlans: vlan iterable, each element must be instance of Vlan
    #     :param args: optional parameters for each implementation
    #     :param kwargs: optional parameters for each implementation
    #     :return: nothing
    #     """
    #     return self._current_dev_manager.attach_vlans_to_uplink(vlans=vlans, *args, **kwargs)

    def scan_onu_list(self) -> Generator:
        return self._current_dev_manager.scan_onu_list()

    def get_fibers(self):
        return self._current_dev_manager.get_fibers()

    def get_units_unregistered(self, *args, **kwargs):
        return self._current_dev_manager.get_units_unregistered(*args, **kwargs)

    def get_ports_on_fiber(self, fiber_num: int) -> Iterable:
        return self._current_dev_manager.get_ports_on_fiber(fiber_num=fiber_num)


class PonOnuDeviceStrategy(BaseDeviceStrategy):
    def __init__(self, num=0, name="", status=False, mac: bytes = b"",
                 speed=0, uptime=None, snmp_num=None, *args, **kwargs):
        """
        :param dev_interface: a subclass of devices.device_config.base.BasePONInterface
        :param dev_instance: an instance of devices.models.Device
        :param num: onu number
        :param name: onu name
        :param status: onu status
        :param mac: onu unique mac
        :param speed:
        :param uptime:
        :param snmp_num:
        """
        super().__init__(*args, **kwargs)
        self.num = int(num)
        self.nm = name
        self.st = status
        self._mac: bytes = mac
        self.sp = speed
        self._uptime = int(uptime) if uptime else None
        self.snmp_num = snmp_num

    @abstractmethod
    def read_onu_vlan_info(self):
        raise UnsupportedReadingVlan

    @abstractmethod
    def default_vlan_info(self):
        raise UnsupportedReadingVlan

    @staticmethod
    def get_config_types() -> ListDeviceConfigType:
        """
        Returns all possible config type for this device type
        :return: List instance of DeviceConfigType
        """
        return []

    @abstractmethod
    def remove_from_olt(self, extra_data: dict, **kwargs) -> bool:
        """Removes device from OLT if devices is ONU"""

    @property
    def mac(self) -> str:
        return macbin2str(self._mac)

    @abstractmethod
    def find_onu(self, *args, **kwargs) -> tuple[Optional[int], Optional[str]]:
        """Finds onu by args on OLT, and returns its snmp_info"""
        raise NotImplementedError


class PonONUDeviceStrategyContext(BaseDeviceStrategyContext):
    _current_dev_manager: PonOnuDeviceStrategy

    @property
    def mac(self) -> str:
        return self._current_dev_manager.mac

    def read_onu_vlan_info(self):
        return self._current_dev_manager.read_onu_vlan_info()

    def default_vlan_info(self):
        return self._current_dev_manager.default_vlan_info()

    def get_config_types(self) -> ListDeviceConfigType:
        """
        Returns all possible config type for this device type
        :return: List instance of DeviceConfigType
        """
        return self._current_dev_manager.get_config_types()

    def remove_from_olt(self, extra_data: dict, **kwargs) -> bool:
        """Removes device from OLT if devices is ONU"""
        return self._current_dev_manager.remove_from_olt(extra_data, **kwargs)

    def find_onu(self, *args, **kwargs) -> tuple[Optional[int], Optional[str]]:
        """Finds onu by args on OLT, and returns its snmp_info"""
        return self._current_dev_manager.find_onu(*args, **kwargs)
