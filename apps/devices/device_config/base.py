from dataclasses import dataclass
from typing import Generator, Optional, Iterable, Union, Any
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException


OptionalScriptCallResult = Optional[dict[str, Union[str, Any]]]


class DeviceImplementationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Device implementation error")


class DeviceConfigurationError(DeviceImplementationError):
    pass


class DeviceConsoleError(DeviceImplementationError):
    pass


class DeviceConnectionError(DeviceImplementationError):
    pass


class UnsupportedReadingVlan(DeviceImplementationError):
    pass


class DeviceTimeoutError(DeviceImplementationError):
    status_code = status.HTTP_408_REQUEST_TIMEOUT
    default_detail = _("Device timeout error")


@dataclass
class Vlan:
    vid: int
    title: Optional[str] = None
    native: bool = False
    is_management: bool = False

    def __post_init__(self):
        if self.title is None:
            self.title = f'v{self.vid}'
        elif isinstance(self.title, bytes):
            self.title = self.title.decode()

    def __hash__(self):
        return self.vid

    def __eq__(self, other):
        return self.vid == other.vid


@dataclass
class MacItem:
    vid: int
    name: str
    mac: str
    port: int


Vlans = Iterable[Vlan]
Macs = Generator[MacItem, None, None]
