from typing import Iterable

from networks.models import CustomerIpLeaseModel
from sorm_export.hier_export.base import simple_export_decorator, format_fname
from sorm_export.serializers import networks
from sorm_export.serializers.networks import IpLeaseAddrTypeChoice


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
        'ip_addr_type': IpLeaseAddrTypeChoice.GRAY,  # FIXME: определять вид адреса
        'assign_time': lease.lease_time,
        'mac_addr': lease.mac_address
    } for lease in leases]

    ser = networks.CustomerIpLeaseExportFormat(
        data=dat, many=True
    )
    return ser, f'ISP/abonents/ip_nets_v1_{format_fname(event_time)}.txt'
