import abc
import enum
from typing import Optional, Tuple, Type, TypeVar, overload
from dataclasses import dataclass
from netaddr import EUI

from djing2.lib import LogicError


@dataclass
class SpeedInfoStruct:
    speed_in: float
    speed_out: float
    burst_in: float
    burst_out: float


@dataclass
class CustomerServiceLeaseResult:
    id: int
    username: str
    is_active: bool
    balance: float
    is_dynamic_ip: bool
    auto_renewal_service: bool
    current_service_id: Optional[int]
    dev_port_id: Optional[int] = None
    device_id: Optional[int] = None
    gateway_id: Optional[int] = None
    speed: Optional[SpeedInfoStruct] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    is_dynamic: Optional[bool] = False


class AcctStatusType(enum.IntEnum):
    START = 1
    STOP = 2
    UPDATE = 3


T = TypeVar('T')


class IVendorSpecific(abc.ABC):
    @property
    @abc.abstractmethod
    def vendor(self):
        raise NotImplementedError

    @overload
    @staticmethod
    def get_rad_val(data, v: str, fabric_type: Type[T]) -> Optional[T]:
        ...

    @overload
    @staticmethod
    def get_rad_val(data, v: str, fabric_type: Type[T], default: T) -> T:
        ...

    @staticmethod
    def get_rad_val(data, v, fabric_type, default=None):
        k = data.get(v)
        if k:
            if isinstance(k, (str, int)):
                return fabric_type(k)
            k = k.get("value")
            if k:
                return fabric_type(k[0])
        return default

    @abc.abstractmethod
    def parse_option82(self, data) -> Optional[Tuple[str, str]]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_customer_mac(self, data) -> Optional[EUI]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_vlan_id(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def get_service_vlan_id(self, data):
        raise NotImplementedError

    def get_radius_username(self, data) -> Optional[str]:
        v = self.get_rad_val(data, "User-Name", str)
        return str(v) if v else None

    def get_radius_unique_id(self, data):
        return self.get_rad_val(data, "Acct-Unique-Session-Id", str)

    @staticmethod
    def get_speed(speed: SpeedInfoStruct) -> SpeedInfoStruct:
        speed_in = speed.speed_in * 1000000.0
        speed_out = speed.speed_out * 1000000.0
        #brst_in = speed_in / 8.0 * 1.5
        brst_in = speed_in / 8.0
        #brst_out = speed_in / 8.0 * 1.5
        brst_out = speed_in / 8.0
        return SpeedInfoStruct(
            speed_in=speed_in,
            speed_out=speed_out,
            burst_in=brst_in,
            burst_out=brst_out
        )

    @abc.abstractmethod
    def get_auth_session_response(
        self,
        db_result: CustomerServiceLeaseResult
    ) -> Optional[dict]:
        raise NotImplementedError

    def get_acct_status_type(self, request) -> AcctStatusType:
        dat = request.data
        act_type = self.get_rad_val(dat, "Acct-Status-Type", str)
        if isinstance(act_type, int) or (isinstance(act_type, str) and act_type.isdigit()):
            act_type = int(act_type)
            r_map = {
                1: AcctStatusType.START,
                2: AcctStatusType.STOP,
                3: AcctStatusType.UPDATE
            }
            r = r_map.get(act_type)
        elif isinstance(act_type, str):
            act_type = str(act_type)
            r_map = {
                "Start": AcctStatusType.START,
                "Stop": AcctStatusType.STOP,
                "Interim-Update": AcctStatusType.UPDATE,
            }
            r = r_map.get(act_type)
        else:
            raise LogicError('Unknown act_type: "%s" - %s' % (act_type, type(act_type)))
        if r is None:
            raise LogicError('Unknown act_type: "%s" - %s' % (act_type, type(act_type)))
        return r
