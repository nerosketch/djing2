from radiusapp.vendor_base import IVendorSpecific


class MikrotikVendorSpecific(IVendorSpecific):
    vendor = 'mikrotik'

    def parse_option82(self, data):
        aget_remote_id = self.get_rad_val(data, 'Agent-Remote-Id')
        aget_circ_id = self.get_rad_val(data, 'Agent-Circuit-Id')
        return aget_remote_id, aget_circ_id

    def get_customer_mac(self, data):
        return self.get_rad_val(data, 'User-Name')

    def get_vlan_id(self, data):
        return 0
