from abc import ABC, abstractmethod


from typing import Generator, Optional, Dict, AnyStr, Tuple, Any, List, Type
from easysnmp import Session, EasySNMPConnectionError

from django.utils.translation import gettext_lazy as _, gettext
from django.db import models

from devices.device_config.base import DeviceImplementationError, DeviceConnectionError
from djing2.lib import RuTimedelta, macbin2str


class SNMPWorker(Session):
    def __init__(self, hostname: str, *args, **kwargs):
        if not hostname:
            raise DeviceImplementationError(gettext("Hostname required for snmp"))
        try:
            super().__init__(hostname=hostname, *args, **kwargs)
        except OSError as e:
            raise DeviceConnectionError(e)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self.sess_ptr

    def set_int_value(self, oid: str, value: int) -> bool:
        try:
            return self.set(oid, value, "i")
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
                snmpnum = v.oid.split(".")[-1:]
                yield v.value, snmpnum[0] if len(snmpnum) > 0 else None
        except EasySNMPConnectionError as err:
            raise DeviceConnectionError(err)

    def get_next_keyval(self, oid) -> Tuple:
        v = self.get_next(oid)
        if not v:
            return None, None
        snmpnum = v.oid.split(".")[-1:]
        return v.value, snmpnum[0] if len(snmpnum) > 0 else None

    def get_list_with_oid(self, oid) -> Generator:
        try:
            for v in self.walk(oid):
                res_oid = v.oid.split(".")
                yield v.value, res_oid
        except EasySNMPConnectionError as err:
            raise DeviceConnectionError(err)

    def get_item(self, oid) -> Any:
        try:
            v = self.get(oid).value
            if isinstance(v, str):
                if v and v != "NOSUCHINSTANCE":
                    return v.encode()
                return None
            return v
        except EasySNMPConnectionError as err:
            raise DeviceConnectionError(err)

    def get_item_plain(self, oid) -> Any:
        try:
            v = self.get(oid).value
            if isinstance(v, str):
                if v and v != "NOSUCHINSTANCE":
                    return v
                return None
            return v
        except EasySNMPConnectionError as err:
            raise DeviceConnectionError(err)


class BaseDeviceInterface(BaseSNMPWorker):

    """How much ports is available for switch"""

    ports_len: int

    def __init__(self, dev_instance=None, host: str = None, snmp_community="public"):
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

    def delete_vlan(self, vid: int, is_management: bool) -> bool:
        _vlan_gen = (v for v in (Vlan(vid=vid, title=None, is_management=is_management, native=False),))
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

    def reboot(self, save_before_reboot=False) -> Tuple[int, AnyStr]:
        """
        Send signal reboot to device
        :param save_before_reboot:
        :return: tuple of command return number and text of operation
        """
        return 5, _("Reboot not ready")

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


class PortVlanConfigModeChoices(models.TextChoices):
    TRUNK = ('trunk', _('Trunk'))
    ACCESS = ('access', _('Access'))


class DeviceConfigType:
    title: str
    short_code: str
    accept_vlan: bool

    def __init__(self, title: Optional[str] = None, code: Optional[str] = None):
        if title:
            self.title = title
        if code:
            self.short_code = code
        if not isinstance(self.title, str):
            raise TypeError
        if not isinstance(self.short_code, str):
            raise TypeError

    @classmethod
    @abstractmethod
    def entry_point(cls, config: dict, device, *args, **kwargs) -> OptionalScriptCallResult:
        """
        This method is entry point for all custom device automation
        :param config: Dict from views.apply_device_onu_config_template
        :param device: devices.models.Device instance
        :param args:
        :param kwargs:
        :return: Result from call automation script, that is then
                 returned to user side by HTTP
        """
        raise NotImplementedError

    def __call__(self, *args, **kwargs) -> OptionalScriptCallResult:
        return self.entry_point(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.title)

    @classmethod
    def to_dict(cls):
        return {"title": cls.title, "code": cls.short_code, "accept_vlan": cls.accept_vlan}


ListDeviceConfigType = List[Type[DeviceConfigType]]


class BasePortInterface(ABC):
    def __init__(
        self,
        dev_interface: BaseSwitchInterface,
        num=0,
        name="",
        status=False,
        mac: bytes = b"",
        speed=0,
        uptime=None,
        snmp_num=None,
        *args,
        **kwargs,
    ):
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
            "num": self.num,
            "snmp_number": self.snmp_num,
            "name": self.nm,
            "status": self.st,
            "mac_addr": self.mac,
            "speed": int(self.sp or 0),
            "uptime": str(RuTimedelta(seconds=self._uptime / 100)) if self._uptime else None,
        }

    @staticmethod
    @abstractmethod
    def get_config_types() -> ListDeviceConfigType:
        """
        Returns all possible config type for this device type
        :return: List instance of DeviceConfigType
        """
        raise NotImplementedError


class BaseDeviceStrategy(ABC):
    model_instance = None

    def __init__(self, model_instance):
        self.model_instance = model_instance

    @abstractmethod
    def get_device_name(self) -> str:
        """Return device name by snmp"""
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """Base device interface"""

    @abstractmethod
    def get_uptime(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def is_use_device_port(self) -> bool:
        """True if used device port while opt82 authorization"""
        raise NotImplementedError

    @property
    @abstractmethod
    def has_attachable_to_customer(self) -> bool:
        """True if used device port while opt82 authorization"""
        raise NotImplementedError

    @staticmethod
    def validate_extra_snmp_info(v: str) -> None:
        raise NotImplementedError


global_device_types_map: Dict[int, Type[BaseDeviceStrategy]] = {}


class BaseDeviceStrategyContext(ABC):
    _current_dev_manager: BaseDeviceStrategy

    def __init__(self, model_instance):
        self.model_instance = model_instance
        dev_type = int(model_instance.dev_type)
        self.set_device_type(unique_code=dev_type)

    def set_device_type(self, unique_code: int):
        kls = global_device_types_map.get(unique_code)
        if kls is not None:
            self._current_dev_manager = kls(
                model_instance=self.model_instance
            )
        else:
            raise TypeError(f'Device manager with code "{unique_code}" does not exists')

    @staticmethod
    def add_device_type(unique_code: int, device_class: Type[BaseDeviceStrategy]):
        global global_device_types_map
        global_device_types_map[unique_code] = device_class

    def get_description(self):
        return self._current_dev_manager.description

    @property
    def has_attachable_to_customer(self) -> bool:
        """Can connect device to customer"""
        return self._current_dev_manager.has_attachable_to_customer

    # def get_snmp_worker(self):
    #     return BaseSNMPWorker(hostname=)

    def get_device_name(self) -> str:
        """Return device name by snmp"""
        return self._current_dev_manager.get_device_name()

    @property
    def description(self) -> str:
        """Base device interface"""
        return self._current_dev_manager.description

    def get_uptime(self) -> str:
        return self._current_dev_manager.get_uptime()

    @property
    def is_use_device_port(self) -> bool:
        """True if used device port while opt82 authorization"""
        return self._current_dev_manager.is_use_device_port

    def get_details(self) -> dict:
        """
        Return basic information by SNMP or other method
        :return: dict of information
        """
        mng = self._current_dev_manager
        return {
            "uptime": mng.get_uptime(),
            "name": mng.get_device_name(),
            "description": mng.description,
            "has_attachable_to_customer": self.has_attachable_to_customer,
            "is_use_device_port": mng.is_use_device_port,
        }
