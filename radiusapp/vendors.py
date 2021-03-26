from typing import Optional, Tuple

from customers.models import CustomerService, Customer
from djing2.lib import macbin2str, safe_int
from radiusapp.models import CustomerRadiusSession, FetchSubscriberLeaseResponse

from radiusapp.vendor_specific import vendor_classes
from radiusapp.vendor_base import IVendorSpecific


def parse_opt82(remote_id: bytes, circuit_id: bytes) -> Tuple[Optional[str], int]:
    # 'remote_id': '0x000600ad24d0c544', 'circuit_id': '0x000400020002'
    mac, port = None, 0
    remote_id, circuit_id = bytes(remote_id), bytes(circuit_id)
    if circuit_id.startswith(b'ZTE'):
        mac = remote_id.decode()
    else:
        try:
            port = safe_int(circuit_id[-1:][0])
        except IndexError:
            port = 0
        if len(remote_id) >= 6:
            mac = macbin2str(remote_id[-6:])
    return mac, port


class VendorManager(object):
    vendor_class: Optional[IVendorSpecific] = None

    def __init__(self, vendor_name: str):
        vc = [v for v in vendor_classes if v.vendor == vendor_name]
        if len(vc) == 1:
            self.vendor_class = vc[0]

    def get_opt82(self, data):
        if self.vendor_class:
            return self.vendor_class.parse_option82(data=data)

    @staticmethod
    def build_dev_mac_by_opt82(agent_remote_id: str, agent_circuit_id: str):
        dig = int(agent_remote_id, base=16)
        agent_remote_id = dig.to_bytes((dig.bit_length() + 7) // 8, 'big')
        dig = int(agent_circuit_id, base=16)
        agent_circuit_id = dig.to_bytes((dig.bit_length() + 7) // 8, 'big')

        dev_mac, dev_port = parse_opt82(agent_remote_id, agent_circuit_id)
        return dev_mac, dev_port

    def get_customer_mac(self, data):
        if self.vendor_class:
            return self.vendor_class.get_customer_mac(data)

    def get_vlan_id(self, data):
        if self.vendor_class:
            return self.vendor_class.get_vlan_id(data)

    def get_radius_username(self, data):
        if self.vendor_class:
            return self.vendor_class.get_radius_username(data)

    def get_radius_unique_id(self, data):
        if self.vendor_class:
            return self.vendor_class.get_radius_unique_id(data)

    def get_auth_guest_session_response(self, guest_session: CustomerRadiusSession, data) -> dict:
        if self.vendor_class:
            return self.vendor_class.get_auth_guest_session_response(guest_session, data)

    def get_auth_session_response(self, subscriber_lease: FetchSubscriberLeaseResponse,
                                  customer_service: CustomerService,
                                  customer: Customer,
                                  request_data) -> dict:
        if vendor_classes:
            return self.vendor_class.get_auth_session_response(
                subscriber_lease=subscriber_lease,
                customer_service=customer_service,
                customer=customer,
                request_data=request_data
            )

    def get_acct_status_type(self, request):
        if self.vendor_class:
            return self.vendor_class.get_acct_status_type(request)