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


class SNMPBaseWorker(ABC):
    ses = None

    def __init__(self, ip: Optional[str], community='public', ver=2):
        if ip is None or ip == '':
            raise DeviceImplementationError(gettext('Ip address is required'))
        self._ip = ip
        self._community = community
        self._ver = ver

    def start_ses(self):
        if self.ses is None:
            self.ses = Session(
                hostname=self._ip, community=self._community,
                version=self._ver
            )

    def set_int_value(self, oid: str, value):
        self.start_ses()
        return self.ses.set(oid, value, 'i')

    def get_list(self, oid) -> Generator:
        self.start_ses()
        for v in self.ses.walk(oid):
            yield v.value

    def get_list_keyval(self, oid) -> Generator:
        self.start_ses()
        for v in self.ses.walk(oid):
            snmpnum = v.oid.split('.')[-1:]
            yield v.value, snmpnum[0] if len(snmpnum) > 0 else None

    def get_item(self, oid):
        self.start_ses()
        v = self.ses.get(oid).value
        if v != 'NOSUCHINSTANCE':
            return v


class DevBase(Telnet, SNMPBaseWorker, metaclass=ABCMeta):
    def __init__(self, dev_instance, prompt: bytes, endl: bytes = b'\n', port=23, *args, **kwargs):
        super().__init__(port=port, *args, **kwargs)
        self.db_instance = dev_instance
        self.prompt = prompt
        if isinstance(endl, bytes):
            self.endl = endl
        else:
            self.endl = str(endl).encode()
        SNMPBaseWorker.__init__(self, dev_instance.ip_address, dev_instance.man_passw, 2)

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
    def ports_len(self) -> int:
        """How much ports is available for switch"""

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
    def register_device(self, extra_data: Dict) -> None:
        pass

    def remove_from_olt(self, extra_data: Dict) -> None:
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

    #############################
    #      Telnet access
    #############################

    def login(self, login_prompt: bytes, login: str, password_prompt: bytes, password: str) -> bool:
        self.read_until(login_prompt)
        self.write(login)
        self.read_until(password_prompt)
        self.write(password)
        self.read_until(self.prompt)
        # self._disable_prompt()
        return True

    def write(self, buffer: AnyStr) -> None:
        if isinstance(buffer, bytes):
            return super().write(buffer + self.endl)
        return super().write(buffer.encode() + self.endl)

    def read_until(self, match, timeout=None) -> bytes:
        if isinstance(match, bytes):
            return super().read_until(match=match, timeout=timeout)
        return super().read_until(match=str(match).encode(), timeout=timeout)

    @staticmethod
    def _normalize_name(name: str) -> str:
        vname = translit(name, language_code='ru', reversed=True)
        return re.sub(r'\W+', '_', vname)[:32]

    @abstractmethod
    def read_port_vlan_info(self, port: int) -> Vlans:
        """
        Read info about all vlans on port
        :param port: Port number
        :return: Vlan list
        """
        raise NotImplementedError

    @abstractmethod
    def read_all_vlan_info(self) -> Vlans:
        """
        Read info about all vlans
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
    def read_mac_address_vlan(self, vid: int) -> Macs:
        """
        Read FDB in vlan
        :param vid
        :return: Mac list
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

    def create_vlan(self, vid: int, name: str) -> bool:
        _vlan_gen = (v for v in (Vlan(vid=vid, name=name),))
        return self.create_vlans(_vlan_gen)

    @abstractmethod
    def delete_vlans(self, vlan_list: Vlans) -> bool:
        """
        Delete vlans from switch
        :param vlan_list:
        :return: Operation result
        """
        raise NotImplementedError

    def delete_vlan(self, vid: int) -> bool:
        _vlan_gen = (v for v in (Vlan(vid=vid, name=None),))
        return self.delete_vlans(_vlan_gen)

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

    def to_dict(self) -> dict:
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
