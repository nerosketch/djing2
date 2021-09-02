import re
from abc import abstractmethod
from typing import Optional
from transliterate import translit
from django.conf import settings
from devices.device_config.base import Vlan, Vlans, Macs
from devices.device_config.base_device_strategy import BaseDeviceStrategyContext, PortVlanConfigModeChoices


class SwitchDeviceStrategyContext(BaseDeviceStrategyContext):
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
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

    def _get_vid_name(self, vid: int) -> str:
        return self.get_item(".1.3.6.1.2.1.17.7.1.4.3.1.1.%d" % vid)

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

    @staticmethod
    def _normalize_name(name: str, vid: Optional[int] = None) -> str:
        if name:
            language_code = getattr(settings, "LANGUAGE_CODE", "ru")
            vname = translit(name, language_code=language_code, reversed=True)
            return re.sub(r"\W+", "_", vname)[:32]
        if vid and isinstance(vid, int):
            return 'v%d' % vid
        return ''
