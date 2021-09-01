from typing import Dict, Generator, Optional, Tuple
from abc import abstractmethod

from devices.device_config.base import Vlans
from devices.device_config.base_device_strategy import BaseDeviceStrategyContext


class PonDeviceStrategyContext(BaseDeviceStrategyContext):
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)

    @abstractmethod
    def remove_from_olt(self, extra_data: Dict) -> bool:
        """Removes device from OLT if devices is ONU"""

    @abstractmethod
    def attach_vlans_to_uplink(self, vlans: Vlans, *args, **kwargs) -> None:
        """
        Attach vlan to uplink port
        :param vlans: vlan iterable, each element must be instance of Vlan
        :param args: optional parameters for each implementation
        :param kwargs: optional parameters for each implementation
        :return: nothing
        """
        raise NotImplementedError

    @abstractmethod
    def scan_onu_list(self) -> Generator:
        raise NotImplementedError

    @abstractmethod
    def get_fibers(self) -> Generator:
        raise NotImplementedError
