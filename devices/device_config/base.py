import re
from abc import ABC, abstractmethod
from collections import namedtuple
# from telnetlib import Telnet
from typing import Generator, Optional, Dict, AnyStr, Tuple, Any, List, Callable
from easysnmp import Session, EasySNMPConnectionError
from transliterate import translit

from django.utils.translation import gettext_lazy as _, gettext
from django.conf import settings
from djing2.lib import RuTimedelta, macbin2str


OptionalScriptCallResult = Optional[Dict[int, str]]


class DeviceImplementationError(NotImplementedError):
    pass


class DeviceConfigurationError(DeviceImplementationError):
    pass


class DeviceConsoleError(Exception):
    pass


class DeviceConnectionError(ConnectionError):
    pass


class Vlan(namedtuple('Vlan', 'vid title native is_management')):

    def __new__(cls, vid: int, title: str, native: bool = False, is_management: bool = False):
        if title:
            if isinstance(title, bytes):
                title = ''.join(chr(c) for c in title if chr(c).isalpha())
            else:
                title = ''.join(filter(str.isalpha, title))
        return super().__new__(
            cls, vid=vid, title=title, native=native,
            is_management=is_management
        )


Vlans = Generator[Vlan, None, None]
MacItem = namedtuple('MacItem', 'vid name mac port')
Macs = Generator[MacItem, None, None]


class BaseSNMPWorker(Session):
    def __init__(self, hostname: str=None, version=2, *args, **kwargs):
        if not hostname:
            raise DeviceImplementationError(gettext('Hostname required for snmp'))
        try:
            super().__init__(
                hostname=hostname,
                version=version, *args, **kwargs
            )
        except OSError as e:
            raise DeviceConnectionError(e)

    def set_int_value(self, oid: str, value: int) -> bool:
        try:
            return self.set(oid, value, 'i')
        except EasySNMPConnectionError as err:
            raise DeviceConnectionError(err)

    def get_list(self, oid) -> Generator:
        try:
            for v in self.walk(oid):
                yield v.value
        except EasySNMPConnectionError as err:
            raise DeviceConnectionError(err)

    def get_list_keyval(self, oid) -> Generator:
        try:
            for v in self.walk(oid):
                snmpnum = v.oid.split('.')[-1:]
                yield v.value, snmpnum[0] if len(snmpnum) > 0 else None
        except EasySNMPConnectionError as err:
            raise DeviceConnectionError(err)

    def get_next_keyval(self, oid) -> Tuple:
        v = self.get_next(oid)
        if not v:
            return None, None
        snmpnum = v.oid.split('.')[-1:]
        return v.value, snmpnum[0] if len(snmpnum) > 0 else None

    def get_list_with_oid(self, oid) -> Generator:
        try:
            for v in self.walk(oid):
                res_oid = v.oid.split('.')
                yield v.value, res_oid
        except EasySNMPConnectionError as err:
            raise DeviceConnectionError(err)

    def get_item(self, oid) -> Any:
        try:
            v = self.get(oid).value
            if isinstance(v, str):
                if v and v != 'NOSUCHINSTANCE':
                    return v.encode()
                return None
            return v
        except EasySNMPConnectionError as err:
            raise DeviceConnectionError(err)

    def get_item_plain(self, oid) -> Any:
        try:
            v = self.get(oid).value
            if isinstance(v, str):
                if v and v != 'NOSUCHINSTANCE':
                    return v
                return None
            return v
        except EasySNMPConnectionError as err:
            raise DeviceConnectionError(err)


class BaseDeviceInterface(BaseSNMPWorker):
    def __init__(self, dev_instance=None, host: str=None, snmp_community='public'):
        """
        :param dev_instance: an instance of devices.models.Device
        :param host: device host address
        """
        BaseSNMPWorker.__init__(self, hostname=host, community=snmp_community)
        # BaseTelnetWorker.__init__(self, host=host)
        self.dev_instance = dev_instance

    def create_vlans(self, vlan_list: Vlans) -> bool:
        """
        Create new vlan with name
        :param vlan_list:
        :return: Operation result
        """
        raise NotImplementedError

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

    def delete_vlan(self, vid: int) -> bool:
        _vlan_gen = (v for v in (Vlan(vid=vid, title=None),))
        return self.delete_vlans(_vlan_gen)

    def read_all_vlan_info(self) -> Vlans:
        """
        Read info about all vlans
        :return: Vlan list
        """
        raise NotImplementedError

    def read_mac_address_vlan(self, vid: int) -> Macs:
        """
        Read FDB in vlan
        :param vid
        :return: Mac list
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """Base device interface"""

    def reboot(self, save_before_reboot=False) -> Tuple[int, AnyStr]:
        """
        Send signal reboot to device
        :param save_before_reboot:
        :return: tuple of command return number and text of operation
        """
        return 5, _('Reboot not ready')

    @abstractmethod
    def get_device_name(self) -> str:
        """Return device name by snmp"""

    @abstractmethod
    def get_uptime(self) -> str:
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
        If validation failed then raise en exception from
        devapp.expect_scripts.ExpectValidationError
        with description of error.
        :param v: String value for validate
        """
        raise NotImplementedError

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
            'uptime': self.get_uptime(),
            'name': self.get_device_name(),
            'description': self.description,
            'has_attachable_to_customer': self.has_attachable_to_customer,
            'is_use_device_port': self.is_use_device_port
        }


class BaseSwitchInterface(BaseDeviceInterface):
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
        pass

    @property
    @abstractmethod
    def ports_len(self) -> int:
        """How much ports is available for switch"""

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

    def attach_vlans_to_port(self, vlan_list: Vlans, port_num: int) -> bool:
        """
        Attach vlan set to port
        :param vlan_list:
        :param port_num:
        :return: Operation result
        """
        raise NotImplementedError

    @abstractmethod
    def attach_vlan_to_port(self, vlan: Vlan, port: int, tag: bool = True) -> bool:
        """
        Attach vlan to switch port
        :param vid:
        :param port:
        :param tag: Tagged if True or untagged otherwise
        :return:
        """
        _vlan_gen = (v for v in (vlan,))
        return self.attach_vlans_to_port(_vlan_gen, port)

    def _get_vid_name(self, vid: int) -> str:
        return self.get_item('.1.3.6.1.2.1.17.7.1.4.3.1.1.%d' % vid)

    @abstractmethod
    def detach_vlan_from_port(self, vlan: Vlan, port: int) -> bool:
        """
        Detach vlan from switch port
        :param vlan:
        :param port:
        :return: Operation result
        """
        raise NotImplementedError

    @staticmethod
    def _normalize_name(name: str) -> str:
        language_code = getattr(settings, 'LANGUAGE_CODE', 'ru')
        vname = translit(name, language_code=language_code, reversed=True)
        return re.sub(r'\W+', '_', vname)[:32]


class BaseScriptModule(Callable, ABC):
    """
    This class is base for all custom automation for devices
    """

    @abstractmethod
    def entry_point(self, *args, **kwargs) -> OptionalScriptCallResult:
        """
        This method is entry point for all custom device automation
        :param args:
        :param kwargs:
        :return: Result from call automation script, that is then
                 returned to user side by HTTP
        """
        raise NotImplementedError

    def __call__(self, *args, **kwargs):
        return self.entry_point(*args, **kwargs)


class DeviceConfigType(object):
    title: str
    script_module: BaseScriptModule
    short_code: str

    def __init__(self, title: str, script: BaseScriptModule, code: str):
        if not isinstance(title, str):
            raise TypeError
        if not isinstance(code, str):
            raise TypeError
        if not issubclass(script.__class__, BaseScriptModule):
            raise TypeError('script must be subclass of "BaseScriptModule"')
        self.title = title
        self.script_module = script
        self.short_code = code

    def __call__(self, *args, **kwargs) -> OptionalScriptCallResult:
        if self.script_module is None:
            raise RuntimeError('script_module is None')
        return self.script_module(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.title)


ListDeviceConfigType = List[DeviceConfigType]


class BasePortInterface(ABC):
    def __init__(self, dev_interface: BaseSwitchInterface, num=0, name='', status=False, mac: bytes=b'',
                 speed=0, uptime=None, snmp_num=None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.num = int(num)
        self.snmp_num = int(num) if snmp_num is None else int(snmp_num)
        self.nm = name
        self.st = status
        self._mac: bytes = mac
        self.sp = speed
        self._uptime = int(uptime) if uptime else None
        self.dev_interface = dev_interface

    @property
    def mac(self) -> str:
        return macbin2str(self._mac)

    def to_dict(self) -> dict:
        return {
            'num': self.num,
            'snmp_number': self.snmp_num,
            'name': self.nm,
            'status': self.st,
            'mac_addr': self.mac,
            'speed': int(self.sp or 0),
            'uptime': str(RuTimedelta(seconds=self._uptime / 100)) if self._uptime else None
        }

    @staticmethod
    @abstractmethod
    def get_config_types() -> ListDeviceConfigType:
        """
        Returns all possible config type for this device type
        :return: List instance of DeviceConfigType
        """
        raise NotImplementedError


class BasePONInterface(BaseDeviceInterface):
    @abstractmethod
    def register_device(self, extra_data: Dict) -> None:
        pass

    @abstractmethod
    def remove_from_olt(self, extra_data: Dict) -> None:
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


class BasePON_ONU_Interface(BaseDeviceInterface):
    def __init__(self,
                 num=0, name='', status=False, mac: bytes=b'',
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

    def mac(self) -> str:
        return macbin2str(self._mac)

    @abstractmethod
    def get_fiber_str(self):
        return '¯ \ _ (ツ) _ / ¯'

    @abstractmethod
    def read_onu_vlan_info(self):
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def get_config_types() -> ListDeviceConfigType:
        """
        Returns all possible config type for this device type
        :return: List instance of DeviceConfigType
        """
        return []


def port_template(fn):
    def _wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    _wrapper.is_port_template = True
    return _wrapper
