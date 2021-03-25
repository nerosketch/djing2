from .juniper import JuniperVendorSpecific
from .mikrotik import MikrotikVendorSpecific

vendor_classes = (JuniperVendorSpecific(), MikrotikVendorSpecific())

__all__ = ('JuniperVendorSpecific', 'MikrotikVendorSpecific', 'vendor_classes',)
