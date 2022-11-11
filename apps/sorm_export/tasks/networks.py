from datetime import datetime
from typing import Optional

from djing2 import celery_app
from sorm_export.hier_export.base import format_fname
from sorm_export.hier_export.networks import get_addr_type
from sorm_export.models import ExportStampTypeEnum
from sorm_export.tasks.task_export import task_export
from sorm_export.serializers import networks as sorm_networks_serializers


@celery_app.task
def export_static_ip_leases_task_finish(customer_id: int, ip_address: str, lease_time: float,
                                        mac_address: str, event_time: Optional[float] = None):
    if event_time is None:
        event_time = datetime.now()
    else:
        event_time = datetime.fromtimestamp(event_time)
    lease_time = datetime.fromtimestamp(lease_time)
    dat = [{
        'customer_id': customer_id,
        'ip_addr': ip_address,
        'ip_addr_type': get_addr_type(ip_address),
        'assign_time': lease_time,
        'mac_addr': mac_address,
        'dead_time': event_time
    }]

    ser = sorm_networks_serializers.CustomerIpLeaseExportFormat(
        data=dat, many=True
    )
    ser.is_valid(raise_exception=True)
    task_export(
        ser.data,
        f'ISP/abonents/ip_nets_v1_{format_fname(event_time)}.txt',
        ExportStampTypeEnum.NETWORK_STATIC_IP
    )
