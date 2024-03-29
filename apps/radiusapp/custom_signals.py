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
#    instance_queryset - CustomerIpLeaseModel Queryset in instance is None
#    data - all raw data from radius request
#    counters - instance of radiusapp.vendor_base.RadiusCounters dataclass
#    ip_addr - customer ip address from radius request
#    radius_unique_id - obviously
#    customer_mac: netaddr.EUI instance -  customer device mac address from radius request
radius_acct_stop_signal = Signal()


# Sends while radius send acct-update event
# attrs:
#    sender - CustomerIpLeaseModel
#    instance - CustomerIpLeaseModel instance or None, if instance_queryset is None
#    instance_queryset - CustomerIpLeaseModel Queryset if instance is None
#    data - all raw data from radius request
#    counters - instance of radiusapp.vendor_base.RadiusCounters dataclass
#    radius_unique_id - obviously
#    ip_addr - customer ip address from radius request
#    customer_mac: Optional[netaddr.EUI] instance -  customer device mac address from radius request
radius_auth_update_signal = Signal()
