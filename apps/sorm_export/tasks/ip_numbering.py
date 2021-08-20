from datetime import datetime
from uwsgi_tasks import task
from sorm_export.tasks.task_export import task_export
from sorm_export.hier_export.ip_numbering import (
    export_ip_numbering,
    export_ip_numbering_stop_using
)
from networks.models import NetworkIpPool


@task()
def export_ip_numbering_task(ip_pool_id: int, event_time=None):
    pools = NetworkIpPool.objects.filter(pk=ip_pool_id)
    if pools.exists():
        dat, fname = export_ip_numbering(pools=pools, event_time=event_time)
        task_export(data, fname, ExportStampTypeEnum.IP_NUMBERING)


@task()
def export_ip_numbering_stop_using_task(ip_net: str, descr: str,
                                        start_usage_time: datetime,
                                        event_time: datetime):
    dat, fname = export_ip_numbering_stop_using(
        ip_net=ip_net,
        descr=descr,
        start_usage_time=start_usage_time,
        event_time=event_time
    )
    task_export(data, fname, ExportStampTypeEnum.IP_NUMBERING)
