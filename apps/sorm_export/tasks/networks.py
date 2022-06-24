from datetime import datetime
from uwsgi_tasks import task

from sorm_export.hier_export.base import format_fname
from sorm_export.hier_export.networks import get_addr_type
from sorm_export.models import ExportStampTypeEnum
from sorm_export.tasks.task_export import task_export
from sorm_export.serializers import networks as sorm_networks_serializers


#@task()
#def export_static_ip_leases_task(customer_lease_id_list: List[int], event_time=None):
#    leases = CustomerIpLeaseModel.objects.filter(pk__in=customer_lease_id_list).exclude(customer=None)
#    try:
#        IpLeaseExportTree(event_time=event_time).exportNupload(queryset=leases)
#    except ExportFailedStatus as err:
#        logger.error(err)


@task()
def export_static_ip_leases_task_finish(customer_id: int, ip_address: str, lease_time: datetime,
                                        mac_address: str, event_time=None):
    if event_time is None:
        event_time = datetime.now()
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
