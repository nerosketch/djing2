from typing import Iterable
from ipaddress import ip_address
from networks.models import CustomerIpLeaseModel
from sorm_export.hier_export.base import simple_export_decorator, format_fname
from sorm_export.serializers import networks


def get_addr_type(ip) -> networks.IpLeaseAddrTypeChoice:
    # FIXME: identify VPN address type.
    _addr = ip_address(ip)
    if _addr.is_private:
        return networks.IpLeaseAddrTypeChoice.GRAY
    else:
        return networks.IpLeaseAddrTypeChoice.WHITE


@simple_export_decorator
def export_ip_leases(leases: Iterable[CustomerIpLeaseModel], event_time=None):
    """
    Формат выгрузки IP адресов.
    В этом файле выгружается информация по статическим IP
    адресам и подсетям, выданным абонентам.
    """

    dat = [{
        'customer_id': lease.customer_id,
        'ip_addr': lease.ip_address,
        'ip_addr_type': get_addr_type(lease.ip_address),
        'assign_time': lease.lease_time,
        'mac_addr': lease.mac_address
    } for lease in leases]

    ser = networks.CustomerIpLeaseExportFormat(
        data=dat, many=True
    )
    return ser, f'ISP/abonents/ip_nets_v1_{format_fname(event_time)}.txt'
