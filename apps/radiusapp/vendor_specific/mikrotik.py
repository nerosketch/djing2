from netaddr import EUI
from netfields.mac import mac_unix_common
from rest_framework import status
from radiusapp.vendor_base import (
    IVendorSpecific, SpeedInfoStruct,
    CustomerServiceLeaseResult
)


class MikrotikVendorSpecific(IVendorSpecific):
    vendor = "mikrotik"

    def parse_option82(self, data):
        aget_remote_id = self.get_rad_val(data, "Agent-Remote-Id", str)
        aget_circ_id = self.get_rad_val(data, "Agent-Circuit-Id", str)
        return aget_remote_id, aget_circ_id

    def get_customer_mac(self, data):
        str_mac = self.get_rad_val(data, "User-Name", str)
        if str_mac:
            return EUI(str_mac, dialect=mac_unix_common)

    def get_vlan_id(self, data):
        return 0

    def get_service_vlan_id(self, data):
        return 0

    def get_speed(self, speed: SpeedInfoStruct) -> SpeedInfoStruct:
        return speed

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
