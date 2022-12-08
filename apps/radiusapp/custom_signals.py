from django.dispatch import Signal


# Sends while radius maked new session
# attrs:
#    sender - CustomerIpLeaseModel class
#    instance - CustomerIpLeaseModel instance
#    data - all raw data from radius request
#    ip_addr - customer ip address from radius request
#    customer_mac: netaddr.EUI instance -  customer device mac address from radius request
#    radius_username - obviously, User-Name value from radius
#    customer_ip_lease - networks.models.CustomerIpLeaseModel instance
#    customer - customers.models.Customer instance
#    radius_unique_id - obviously
#    event_time - datetime.now() on fetch request time
radius_acct_start_signal = Signal()


# Sends while radius finished session
# attrs:
#    sender - CustomerIpLeaseModel
#    instance - CustomerIpLeaseModel instance
#    data - all raw data from radius request
#    counters - instance of radiusapp.vendor_base.RadiusCounters dataclass
#    ip_addr - customer ip address from radius request
#    radius_unique_id - obviously
#    customer_mac: netaddr.EUI instance -  customer device mac address from radius request
#    customer - customers.models.Customer instance
radius_acct_stop_signal = Signal()


# Sends while radius send acct-update event
# attrs:
#    sender - CustomerIpLeaseModel
#    instance - CustomerIpLeaseModel instance or None
#    data - all raw data from radius request
#    counters - instance of radiusapp.vendor_base.RadiusCounters dataclass
#    radius_unique_id - obviously
#    ip_addr - customer ip address from radius request
#    customer_mac: Optional[netaddr.EUI] instance -  customer device mac address from radius request
#    customer - customers.models.Customer instance
radius_auth_update_signal = Signal()
