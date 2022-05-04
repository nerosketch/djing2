import abc
import enum
from typing import Optional, Tuple, Type, TypeVar, Union, overload
from dataclasses import dataclass
from netaddr import EUI

from djing2.lib import LogicError
from customers.models import CustomerService, Customer
from networks.models import FetchSubscriberLeaseResponse


class AcctStatusType(enum.IntEnum):
    START = 1
    STOP = 2
    UPDATE = 3

@dataclass
class SpeedInfoStruct:
    speed_in: int
    speed_out: int
    burst_in: int
    burst_out: int


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

    @abc.abstractmethod
    def get_speed(self, service) -> SpeedInfoStruct:
        raise NotImplementedError

    @abc.abstractmethod
    def get_auth_session_response(
        self,
        customer_service: Optional[CustomerService],
        customer: Customer,
        request_data,
        subscriber_lease: Optional[FetchSubscriberLeaseResponse] = None,
    ) -> dict:
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
