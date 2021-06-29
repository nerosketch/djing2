import abc
import enum
from typing import Optional, Tuple
from netaddr import EUI

from customers.models import CustomerService, Customer
from radiusapp.models import FetchSubscriberLeaseResponse


class AcctStatusType(enum.IntEnum):
    START = 1
    STOP = 2
    UPDATE = 3


class IVendorSpecific(abc.ABC):
    @property
    @abc.abstractmethod
    def vendor(self):
        raise NotImplementedError

    @staticmethod
    def get_rad_val(data, v: str, default=None):
        k = data.get(v)
        if k:
            if isinstance(k, (str, int)):
                return k
            k = k.get("value")
            if k:
                return k[0]
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

    def get_radius_username(self, data):
        return self.get_rad_val(data, "User-Name")

    def get_radius_unique_id(self, data):
        return self.get_rad_val(data, "Acct-Unique-Session-Id")

    @abc.abstractmethod
    def get_auth_guest_session_response(self, guest_lease: FetchSubscriberLeaseResponse, data) -> dict:
        raise NotImplementedError

    @abc.abstractmethod
    def get_auth_session_response(
        self,
        subscriber_lease: FetchSubscriberLeaseResponse,
        customer_service: Optional[CustomerService],
        customer: Customer,
        request_data,
    ) -> dict:
        raise NotImplementedError

    def get_acct_status_type(self, request) -> AcctStatusType:
        dat = request.data
        act_type = self.get_rad_val(dat, "Acct-Status-Type")
        if isinstance(act_type, int):
            r_map = {1: AcctStatusType.START, 2: AcctStatusType.STOP, 3: AcctStatusType.UPDATE}
        else:
            r_map = {
                "Start": AcctStatusType.START,
                "Stop": AcctStatusType.STOP,
                "Interim-Update": AcctStatusType.UPDATE,
            }
        return r_map.get(act_type)
