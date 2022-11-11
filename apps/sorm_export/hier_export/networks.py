from ipaddress import ip_address
from networks.models import CustomerIpLeaseModel
from sorm_export.hier_export.base import format_fname, ExportTree
from sorm_export.serializers import networks
from sorm_export.models import ExportStampTypeEnum


def get_addr_type(ip) -> networks.IpLeaseAddrTypeChoice:
    # FIXME: identify VPN address type.
    _addr = ip_address(ip)
    if _addr.is_private:
        return networks.IpLeaseAddrTypeChoice.GRAY
    else:
        return networks.IpLeaseAddrTypeChoice.WHITE


class IpLeaseExportTree(ExportTree[CustomerIpLeaseModel]):
    """
    Формат выгрузки IP адресов.
    В этом файле выгружается информация по статическим IP
    адресам и подсетям, выданным абонентам.
    """
    def get_remote_ftp_file_name(self):
        return f'ISP/abonents/ip_nets_v1_{format_fname(self._event_time)}.txt'

    @classmethod
    def get_export_format_serializer(cls):
        return networks.CustomerIpLeaseExportFormat

    @classmethod
    def get_export_type(cls):
        return ExportStampTypeEnum.NETWORK_STATIC_IP

    def get_item(self, lease: CustomerIpLeaseModel, *args, **kwargs):
        return {
            'customer_id': lease.customer_id,
            'ip_addr': lease.ip_address,
            'ip_addr_type': get_addr_type(lease.ip_address),
            'assign_time': lease.lease_time,
            'mac_addr': lease.mac_address
        }
