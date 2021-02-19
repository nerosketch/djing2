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
