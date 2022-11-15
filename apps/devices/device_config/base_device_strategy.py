from abc import ABC, abstractmethod
from typing import Generator, Optional, Any, Type
from easysnmp import Session, EasySNMPConnectionError
from django.utils.translation import gettext
from devices.device_config.base import (
    DeviceImplementationError, DeviceConnectionError,
    OptionalScriptCallResult, Vlans
)


class SNMPWorker(Session):
    def __init__(self, hostname: str, version=2, *args, **kwargs):
        if not hostname:
            raise DeviceImplementationError(gettext("Hostname required for snmp"))
        try:
            super().__init__(hostname=str(hostname), version=version, *args, **kwargs)
        except OSError as e:
            raise DeviceConnectionError(e) from e

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        del self.sess_ptr

    def set_int_value(self, oid: str, value: int) -> bool:
        try:
            return self.set(oid, value, "i")
        except EasySNMPConnectionError as err:
            raise DeviceConnectionError(err) from err

    def get_list(self, oid) -> Generator:
        try:
            return (v.value for v in self.walk(oid))
        except EasySNMPConnectionError as err:
            raise DeviceConnectionError(err) from err

    def get_list_keyval(self, oid) -> Generator:
        try:
            for v in self.walk(oid):
                snmpnum = v.oid.split(".")[-1:]
                yield v.value, snmpnum[0] if len(snmpnum) > 0 else None
        except EasySNMPConnectionError as err:
            raise DeviceConnectionError(err) from err

    def get_next_keyval(self, oid) -> tuple:
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
            raise DeviceConnectionError(err) from err

    def get_item(self, oid) -> Any:
        try:
            v = self.get(oid).value
            if isinstance(v, str):
                if v and v != "NOSUCHINSTANCE":
                    return v.encode()
                return None
            return v
        except EasySNMPConnectionError as err:
            raise DeviceConnectionError(err) from err

    def get_item_plain(self, oid) -> Any:
        try:
            v = self.get(oid).value
            if isinstance(v, str):
                if v and v != "NOSUCHINSTANCE":
                    return v
                return None
            return v
        except EasySNMPConnectionError as err:
            raise DeviceConnectionError(err) from err


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


ListDeviceConfigType = list[Type[DeviceConfigType]]


class BaseDeviceStrategy(ABC):

    """True if used device port while opt82 authorization"""
    has_attachable_to_customer = False

    tech_code: str
    description: str
    is_use_device_port = False

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

    @staticmethod
    def validate_extra_snmp_info(v: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def read_all_vlan_info(self) -> Vlans:
        """
        Read info about all vlans
        :return: Vlan list
        """
        raise NotImplementedError

    def get_details(self) -> dict:
        """
        Return basic information by SNMP or other method
        :return: dict of information
        """
        return {
            "uptime": self.get_uptime(),
            "name": self.get_device_name(),
            "description": self.description,
            "has_attachable_to_customer": self.has_attachable_to_customer,
            "is_use_device_port": self.is_use_device_port,
        }

    def get_fiber_str(self) -> str:
        return r"¯ \ _ (ツ) _ / ¯"


global_device_types_map: dict[int, Type[BaseDeviceStrategy]] = {}


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

    @staticmethod
    def get_device_types() -> dict[int, Type[BaseDeviceStrategy]]:
        return global_device_types_map

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

    def read_all_vlan_info(self) -> Vlans:
        """
        Read info about all vlans
        :return: Vlan list
        """
        return self._current_dev_manager.read_all_vlan_info()

    def get_details(self) -> dict:
        """
        Return basic information by SNMP or other method
        :return: dict of information
        """
        mng = self._current_dev_manager
        return mng.get_details()

    def get_fiber_str(self) -> str:
        return self._current_dev_manager.get_fiber_str()
