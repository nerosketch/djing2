from netaddr import EUI
from radiusapp.vendor_base import IVendorSpecific
from rest_framework import status


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

    def get_auth_session_response(self, customer_service, customer, request_data, subscriber_lease=None):
        if not customer_service or not customer_service.service:
            service_option = "SERVICE-GUEST"
        else:
            service = customer_service.service

            speed_in = int(service.speed_in * 1000000)
            speed_out = int(service.speed_out * 1000000)
            speed_in_burst, speed_out_burst = service.calc_burst()
            service_option = f"SERVICE-INET({speed_in},{speed_in_burst},{speed_out},{speed_out_burst})"

        res = {
            # 'Framed-IP-Netmask': '255.255.0.0',
            # User-Password - it is a crutch, for config in freeradius
            "User-Password": service_option,
        }
        if subscriber_lease and not subscriber_lease.is_dynamic:
            res.update({
                "Framed-IP-Address": subscriber_lease.ip_address,
            })
        return res, status.HTTP_200_OK
