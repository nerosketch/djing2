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
            'ERX-Service-Activate:1': "SERVICE-INET(10000000,1875000,10000000,1875000)"  # 10 MBit/s
        }

    def get_auth_session_response(self, subscriber_lease, customer_service,
                                  customer, request_data):
        service = customer_service.service

        speed_in = int(service.speed_in * 1000000)
        speed_out = int(service.speed_out * 1000000)
        speed_in_burst = int(speed_in / 8 * 1.5)
        speed_out_burst = int(speed_out / 8 * 1.5)
        return {
            'Framed-IP-Address': subscriber_lease.ip_addr,
            # 'Framed-IP-Netmask': '255.255.0.0',
            'ERX-Service-Activate:1': f'SERVICE-INET({speed_in},{speed_in_burst},{speed_out},{speed_out_burst})',
            # 'ERX-Primary-Dns': '10.12.1.9'
            # 'Acct-Interim-Interval': sess_time.total_seconds()
        }
