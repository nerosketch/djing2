from datetime import timedelta
from netaddr import EUI
from djing2.lib import safe_int
from radiusapp.vendor_base import IVendorSpecific


class JuniperVendorSpecific(IVendorSpecific):
    vendor = "juniper"

    def parse_option82(self, data):
        aget_remote_id = self.get_rad_val(data, "ADSL-Agent-Remote-Id")
        aget_circ_id = self.get_rad_val(data, "ADSL-Agent-Circuit-Id")
        return aget_remote_id, aget_circ_id

    def get_customer_mac(self, data):
        str_mac = self.get_rad_val(data, "ERX-Dhcp-Mac-Addr")
        if str_mac:
            return EUI(str_mac)

    def get_vlan_id(self, data):
        param = self.get_rad_val(data, "NAS-Port-Id")
        if isinstance(param, str) and ":" in param:
            return int(param.split(":")[1].split("-")[1])
        return param

    def get_auth_guest_session_response(self, guest_lease, data):
        return {
            "Framed-IP-Address": guest_lease.ip_addr,
            # 'Acct-Interim-Interval': 300,
            "User-Password": "SERVICE-GUEST",
        }

    def get_auth_session_response(self, subscriber_lease, customer_service, customer, request_data):
        service = customer_service.service

        speed_in = int(service.speed_in * 1000000)
        speed_out = int(service.speed_out * 1000000)
        speed_in_burst = int(speed_in / 8 * 1.5)
        speed_out_burst = int(speed_out / 8 * 1.5)
        res = {
            "Framed-IP-Address": subscriber_lease.ip_addr,
            # 'Framed-IP-Netmask': '255.255.0.0',
            "User-Password": f"SERVICE-INET({speed_in},{speed_in_burst},{speed_out},{speed_out_burst})",
        }
        session_remaining_time = customer_service.calc_session_time(splice=True)
        # + 5 минут потому что в момент, когда закончится сессия,
        # улуга еще будет на учётке. А вот через несколько мин. услуга
        # уже должна перерасчитаться.
        session_remaining_time += timedelta(minutes=5)
        session_remaining_time_secs = safe_int(session_remaining_time.total_seconds())
        if session_remaining_time_secs > 0:
            res.update({"Session-Timeout": session_remaining_time_secs})
        return res
