import re
from abc import ABC, abstractmethod, ABCMeta
from collections import namedtuple
from telnetlib import Telnet
from typing import Generator, Optional, Dict, Union, Iterable, AnyStr, Tuple
from transliterate import translit
from easysnmp import Session

from django.utils.translation import gettext_lazy as _, gettext

from djing2.lib import RuTimedelta


GeneratorOrTuple = Union[Generator, Iterable]


class DeviceImplementationError(NotImplementedError):
    pass


class DeviceConfigurationError(DeviceImplementationError):
    pass


class DeviceConsoleError(Exception):
    pass


Vlan = namedtuple('Vlan', 'vid name')
Vlans = Generator[Vlan, None, None]
MacItem = namedtuple('MacItem', 'vid name mac port')
Macs = Generator[MacItem, None, None]


class BaseSNMPWorker(Session):
    def __init__(self, hostname: str=None, version=2, *args, **kwargs):
        if not hostname:
            raise DeviceImplementationError(gettext('Hostname required for snmp'))
        super().__init__(
            hostname=hostname,
            version=version, *args, **kwargs
        )

    def set_int_value(self, oid: str, value):
        return self.set(oid, value, 'i')

    def get_list(self, oid) -> Generator:
        for v in self.walk(oid):
            yield v.value

    def get_list_keyval(self, oid) -> Generator:
        for v in self.walk(oid):
            snmpnum = v.oid.split('.')[-1:]
            yield v.value, snmpnum[0] if len(snmpnum) > 0 else None

    def get_item(self, oid):
        v = self.get(oid).value
        if v != 'NOSUCHINSTANCE':
            return v


class BaseTelnetWorker(Telnet):
    def __init__(self, host: str, prompt: bytes = b'#', endl: bytes = b'\n', port=23):
        super().__init__(host=host, port=port)
        self.prompt = prompt
        if isinstance(endl, bytes):
            self.endl = endl
        else:
            self.endl = str(endl).encode()

    def login(self, login_prompt: bytes, login: str, password_prompt: bytes, password: str) -> bool:
        self.read_until(login_prompt)
        self.write(login)
        self.read_until(password_prompt)
        self.write(password)
        self.read_until(self.prompt)
        return True

    def write(self, buffer: AnyStr) -> None:
        if isinstance(buffer, bytes):
            return super().write(buffer + self.endl)
        return super().write(buffer.encode() + self.endl)

    def read_until(self, match, timeout=None):
        if isinstance(match, bytes):
            return super().read_until(match=match, timeout=timeout)
        return super().read_until(match=str(match).encode(), timeout=timeout)

    @staticmethod
    def _normalize_name(name: str) -> str:
        vname = translit(name, language_code='ru', reversed=True)
        return re.sub(r'\W+', '_', vname)[:32]


class BaseDeviceInterface(BaseSNMPWorker, BaseTelnetWorker, metaclass=ABCMeta):
    def __init__(self, dev_instance=None, host: str=None, snmp_community='public'):
        """
        :param dev_instance: Instance of devices.models.Device
        :param host: device host address
        """
        BaseSNMPWorker.__init__(self, hostname=host, community=snmp_community)
        BaseTelnetWorker.__init__(self, host=host)
        self.dev_instance = dev_instance

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

    def create_vlan(self, vid: int, name: str) -> bool:
        _vlan_gen = (v for v in (Vlan(vid=vid, name=name),))
        return self.create_vlans(_vlan_gen)

    def delete_vlan(self, vid: int) -> bool:
        _vlan_gen = (v for v in (Vlan(vid=vid, name=None),))
        return self.delete_vlans(_vlan_gen)

    @abstractmethod
    def read_all_vlan_info(self) -> Vlans:
        """
        Read info about all vlans
        :return: Vlan list
        """
        raise NotImplementedError

    @abstractmethod
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

    @classmethod
    def get_description(cls) -> str:
        return getattr(cls, 'description', 'Base device interface')

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
    def get_ports(self) -> GeneratorOrTuple:
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

    @abstractmethod
    def attach_vlan_to_port(self, vid: int, port: int, tag: bool = True) -> bool:
        """
        Attach vlan to switch port
        :param vid:
        :param port:
        :param tag: Tagged if True or untagged otherwise
        :return:
        """
        raise NotImplementedError

    @abstractmethod
    def detach_vlan_from_port(self, vid: int, port: int) -> bool:
        """
        Detach vlan from switch port
        :param vid:
        :param port:
        :return: Operation result
        """
        raise NotImplementedError


class BasePortInterface(ABC):
    def __init__(self, dev_interface: BaseSwitchInterface, num=0, name='', status=False, mac: bytes=b'',
                 speed=0, uptime=None, snmp_num=None, writable=False,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.num = int(num)
        self.snmp_num = int(num) if snmp_num is None else int(snmp_num)
        self.nm = name
        self.st = status
        self._mac: bytes = mac
        self.sp = speed
        self._uptime = int(uptime) if uptime else None
        self.writable = writable
        self.dev_interface = dev_interface

    def mac(self) -> str:
        return ':'.join('%x' % ord(i) for i in self._mac) if self._mac else None

    def to_dict(self) -> dict:
        return {
            'number': self.num,
            'snmp_number': self.snmp_num,
            'name': self.nm,
            'status': self.st,
            'mac_addr': self.mac(),
            'speed': int(self.sp or 0),
            'writable': self.writable,
            'uptime': str(RuTimedelta(seconds=self._uptime / 100)) if self._uptime else None
        }


class BasePONInterface(BaseDeviceInterface):
    @abstractmethod
    def register_device(self, extra_data: Dict) -> None:
        pass

    @abstractmethod
    def remove_from_olt(self, extra_data: Dict) -> None:
        """Removes device from OLT if devices is ONU"""

    @abstractmethod
    def attach_vlans_to_uplink(self, vids: Iterable[int], *args, **kwargs) -> None:
        """
        Attach vlan to uplink port
        :param vids: vid iterable, each element must be instance of Int
        :param args: optional parameters for each implementation
        :param kwargs: optional parameters for each implementation
        :return: nothing
        """
        raise NotImplementedError


class BasePON_ONU_Interface(ABC):
    def __init__(self, dev_interface: BasePONInterface, num=0, name='', status=False, mac: bytes=b'',
                 speed=0, uptime=None, snmp_num=None, writable=False):
        """
        :param dev_interface: a subclass of devices.switch_config.base.BasePONInterface
        :param num: onu number
        :param name: onu name
        :param status: onu status
        :param mac: onu unique mac
        :param speed:
        :param uptime:
        :param snmp_num:
        :param writable:
        """
        self.dev_interface: BasePONInterface = dev_interface
        self.num = int(num)
        self.nm = name
        self.st = status
        self._mac: bytes = mac
        self.sp = speed
        self._uptime = int(uptime) if uptime else None
        self.snmp_num = snmp_num
        self.writable = writable

    def mac(self) -> str:
        return ':'.join('%x' % ord(i) for i in self._mac) if self._mac else None

    def to_dict(self) -> dict:
        return {
            'number': self.num,
            'snmp_number': self.snmp_num,
            'name': self.nm,
            'status': self.st,
            'mac_addr': self.mac(),
            'speed': int(self.sp or 0),
            'writable': self.writable,
            'uptime': str(RuTimedelta(seconds=self._uptime / 100)) if self._uptime else None
        }
