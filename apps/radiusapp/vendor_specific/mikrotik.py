from netaddr import EUI
from netfields.mac import mac_unix_common
from radiusapp.vendor_base import IVendorSpecific, SpeedInfoStruct
from rest_framework import status


class MikrotikVendorSpecific(IVendorSpecific):
    vendor = "mikrotik"

    def parse_option82(self, data):
        aget_remote_id = self.get_rad_val(data, "Agent-Remote-Id")
        aget_circ_id = self.get_rad_val(data, "Agent-Circuit-Id")
        return aget_remote_id, aget_circ_id

    def get_customer_mac(self, data):
        str_mac = self.get_rad_val(data, "User-Name")
        if str_mac:
            return EUI(str_mac, dialect=mac_unix_common)

    def get_vlan_id(self, data):
        return 0

    def get_service_vlan_id(self, data):
        return 0

    def get_speed(self, service) -> SpeedInfoStruct:
        speed_in_burst, speed_out_burst = service.calc_burst()
        return SpeedInfoStruct(
            speed_in=int(service.speed_in),
            speed_out=int(service.speed_out),
            burst_in=speed_in_burst,
            burst_out=speed_out_burst
        )

    def get_auth_session_response(self, customer_service, customer, request_data, subscriber_lease=None):
        # TODO: Make it
        return {
            "Framed-IP-Address": subscriber_lease.ip_addr,
            # 'Acct-Interim-Interval': 300,
            "Mikrotik-Rate-Limit": "1M/1M",
            "Mikrotik-Address-List": "DjingUsersAllowed",
        }, status.HTTP_200_OK
