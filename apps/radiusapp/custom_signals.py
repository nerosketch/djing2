from django.dispatch import Signal


# Sends while radius maked new session
# attrs:
#    sender - CustomerRadiusSession class
#    instance - CustomerRadiusSession instance
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
#    sender - CustomerRadiusSession
#    instance_queryset - CustomerRadiusSession Queryset in instance is None
#    data - all raw data from radius request
#    ip_addr - customer ip address from radius request
#    radius_unique_id - obviously
#    customer_mac: netaddr.EUI instance -  customer device mac address from radius request
radius_acct_stop_signal = Signal()


# Sends while radius send acct-update event
# attrs:
#    sender - CustomerRadiusSession
#    instance - CustomerRadiusSession instance or None, if instance_queryset is None
#    instance_queryset - CustomerRadiusSession Queryset if instance is None
#    data - all raw data from radius request
#    input_octets - count of input octets from start session to now
#    output_octets - count of output octets from start session to now
#    input_packets - count of input packets from start session to now
#    output_packets - count of output packets from start session to now
# radius_auth_update_signal = Signal()
