from netaddr import EUI
from rest_framework import status
from radiusapp.vendor_base import (
    IVendorSpecific,
    CustomerServiceLeaseResult,
    RadiusCounters, gigaword_imp
)


class JuniperVendorSpecific(IVendorSpecific):
    vendor = "juniper"

    def parse_option82(self, data):
        aget_remote_id = self.get_rad_val(data, "ADSL-Agent-Remote-Id" ,str)
        aget_circ_id = self.get_rad_val(data, "ADSL-Agent-Circuit-Id", str)
        return aget_remote_id, aget_circ_id

    def get_customer_mac(self, data):
        str_mac = self.get_rad_val(data, "ERX-Dhcp-Mac-Addr", str)
        if str_mac:
            return EUI(str_mac)

    def get_vlan_id(self, data):
        param = self.get_rad_val(data, "NAS-Port-Id", str)
        if isinstance(param, str) and ":" in param:
            return int(param.split(":")[1].split("-")[1])
        return param

    def get_service_vlan_id(self, data):
        param = self.get_rad_val(data, "NAS-Port-Id", str)
        if isinstance(param, str) and ":" in param:
            return int(param.split(":")[1].split("-")[0])
        return param

    def get_counters(self, data: dict) -> RadiusCounters:
        v_inp_oct = gigaword_imp(
            num=self.get_rad_val(data, "Acct-Input-Octets", int, 0),
            gwords=self.get_rad_val(data, "Acct-Input-Gigawords", int, 0),
        )
        v_out_oct = gigaword_imp(
            num=self.get_rad_val(data, "Acct-Output-Octets", int, 0),
            gwords=self.get_rad_val(data, "Acct-Output-Gigawords", int, 0),
        )
        v_in_pkt = self.get_rad_val(data, "Acct-Input-Packets", int, 0)
        v_out_pkt = self.get_rad_val(data, "Acct-Output-Packets", int, 0)
        return RadiusCounters(
            input_octets=v_inp_oct,
            output_octets=v_out_oct,
            input_packets=v_in_pkt,
            output_packets=v_out_pkt
        )

    def get_auth_session_response(self, db_result: CustomerServiceLeaseResult):
        if db_result.current_service_id and db_result.speed:
            speed = self.get_speed(speed=db_result.speed)
            service_option = "SERVICE-INET(%(si)d,%(bi)d,%(so)d,%(bo)d)" % {
                'si': speed.speed_in,
                'so': speed.speed_out,
                'bi': speed.burst_in,
                'bo': speed.burst_out
            }
        else:
            service_option = "SERVICE-GUEST"

        res = {
            # 'Framed-IP-Netmask': '255.255.0.0',
            # User-Password - it is a crutch, for config in freeradius
            "User-Password": service_option,
        }
        if db_result.ip_address:
            res.update({
                "Framed-IP-Address": db_result.ip_address,
            })
        return res, status.HTTP_200_OK
