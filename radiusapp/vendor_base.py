import abc
from typing import Optional, Tuple

from customers.models import CustomerService, Customer
from radiusapp.models import CustomerRadiusSession, FetchSubscriberLeaseResponse


class IVendorSpecific(abc.ABC):
    @property
    @abc.abstractmethod
    def vendor(self):
        raise NotImplementedError

    @staticmethod
    def get_rad_val(data, v: str):
        k = data.get(v)
        if k:
            k = k.get('value')
            if k:
                return k[0]

    @abc.abstractmethod
    def parse_option82(self, data) -> Optional[Tuple[str, str]]:
        raise NotImplementedError

    @abc.abstractmethod
    def get_customer_mac(self, data):
        raise NotImplementedError

    @abc.abstractmethod
    def get_vlan_id(self, data):
        raise NotImplementedError

    def get_radius_username(self, data):
        return self.get_rad_val(data, 'User-Name')

    def get_radius_unique_id(self, data):
        return self.get_rad_val(data, 'Acct-Unique-Session-Id')

    @abc.abstractmethod
    def get_auth_guest_session_response(self, guest_session: CustomerRadiusSession, data) -> dict:
        raise NotImplementedError

    @abc.abstractmethod
    def get_auth_session_response(self, subscriber_lease: FetchSubscriberLeaseResponse,
                                  customer_service: CustomerService,
                                  customer: Customer,
                                  request_data) -> dict:
        raise NotImplementedError
