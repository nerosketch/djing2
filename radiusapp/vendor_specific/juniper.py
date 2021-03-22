from djing2.lib import safe_int
from radiusapp.vendor_base import IVendorSpecific


class JuniperVendorSpecific(IVendorSpecific):
    vendor = 'juniper'

    def parse_option82(self, data):
        aget_remote_id = self.get_rad_val(data, 'ADSL-Agent-Remote-Id')
        aget_circ_id = self.get_rad_val(data, 'ADSL-Agent-Circuit-Id')
        return aget_remote_id, aget_circ_id

    def get_customer_mac(self, data):
        return self.get_rad_val(data, 'ERX-Dhcp-Mac-Addr')

    def get_vlan_id(self, data):
        return self.get_rad_val(data, 'NAS-Port')

    def get_auth_guest_session_response(self, guest_session, data):
        return {
            # TODO: Optimize it, ip_lease.ip_address fetched from db
            'Framed-IP-Address': guest_session.ip_lease.ip_address,
            # 'Acct-Interim-Interval': 300,
            'User-Password': 'SERVICE-GUEST'
        }

    def get_auth_session_response(self, subscriber_lease, customer_service,
                                  customer, request_data):
        service = customer_service.service

        speed_in = int(service.speed_in * 1000000)
        speed_out = int(service.speed_out * 1000000)
        speed_in_burst = int(speed_in / 8 * 1.5)
        speed_out_burst = int(speed_out / 8 * 1.5)
        res = {
            'Framed-IP-Address': subscriber_lease.ip_addr,
            # 'Framed-IP-Netmask': '255.255.0.0',
            'User-Password': f'SERVICE-INET({speed_in},'
                             f'{speed_in_burst},'
                             f'{speed_out},'
                             f'{speed_out_burst})'
        }
        session_remaining_time = safe_int(customer_service
                                          .calc_session_time()
                                          .total_seconds())
        if session_remaining_time > 0:
            res.update({
                'Session-Timeout': session_remaining_time,
            })
        return res
