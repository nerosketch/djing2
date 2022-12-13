from dataclasses import dataclass
from typing import Generator, Optional, Iterable, Union, Any
from django.utils.translation import gettext as _
from starlette import status
from fastapi import HTTPException


OptionalScriptCallResult = Optional[dict[str, Union[str, Any]]]


class DeviceImplementationError(HTTPException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Device implementation error")

    def __init__(
        self,
        detail: Any = None,
        status_code: Optional[int] = None,
        *args, **kwargs
    ) -> None:
        super().__init__(
            status_code=status_code or self.status_code,
            detail=str(detail) if detail else self.default_detail,
            *args, **kwargs
        )


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
