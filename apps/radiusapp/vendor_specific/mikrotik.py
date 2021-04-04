from radiusapp.vendor_base import IVendorSpecific


class MikrotikVendorSpecific(IVendorSpecific):
    vendor = "mikrotik"

    def parse_option82(self, data):
        aget_remote_id = self.get_rad_val(data, "Agent-Remote-Id")
        aget_circ_id = self.get_rad_val(data, "Agent-Circuit-Id")
        return aget_remote_id, aget_circ_id

    def get_customer_mac(self, data):
        return self.get_rad_val(data, "User-Name")

    def get_vlan_id(self, data):
        return 0

    def get_auth_guest_session_response(self, guest_session, data):
        return {
            # TODO: Optimize it, ip_lease.ip_address fetched from db
            "Framed-IP-Address": guest_session.ip_lease.ip_address,
            # 'Acct-Interim-Interval': 300,
        }

    def get_auth_session_response(self, subscriber_lease, customer_service, customer, request_data):
        return {
            "Framed-IP-Address": subscriber_lease.ip_addr,
            # 'Acct-Interim-Interval': 300,
            "Mikrotik-Rate-Limit": "1M/1M",
            "Mikrotik-Address-List": "DjingUsersAllowed",
        }
