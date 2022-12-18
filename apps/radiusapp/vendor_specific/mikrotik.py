from typing import Mapping

from netaddr import EUI, mac_unix_expanded
from starlette import status
from radiusapp.vendor_base import (
    IVendorSpecific,
    CustomerServiceLeaseResult,
    RadiusCounters
)


class MikrotikVendorSpecific(IVendorSpecific):
    vendor = "mikrotik"

    def parse_option82(self, data: Mapping[str, str]):
        aget_remote_id = self.get_rad_val(data, "Agent-Remote-Id", str)
        aget_circ_id = self.get_rad_val(data, "Agent-Circuit-Id", str)
        return aget_remote_id, aget_circ_id

    def get_customer_mac(self, data):
        str_mac = self.get_rad_val(data, "User-Name", str)
        if str_mac:
            return EUI(str_mac, dialect=mac_unix_expanded)

    def get_vlan_id(self, data):
        return 0

    def get_service_vlan_id(self, data):
        return 0

    def get_counters(self, data: Mapping[str, str]) -> RadiusCounters:
        return RadiusCounters()

    def get_auth_session_response(self, db_result: CustomerServiceLeaseResult):
        # TODO: Make it
        r = {
            "Mikrotik-Rate-Limit": "1M/1M",
            "Mikrotik-Address-List": "DjingUsersAllowed",
            # 'Acct-Interim-Interval': 300,
        }
        if db_result.ip_address:
            r.update({
                "Framed-IP-Address": db_result.ip_address,
            })
        return r, status.HTTP_200_OK
