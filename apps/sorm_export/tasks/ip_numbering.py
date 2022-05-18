from datetime import datetime
from uwsgi_tasks import task
from sorm_export.hier_export.ip_numbering import (
    IpNumberingStopUsageSimpleExportTree,
    IpNumberingExportTree
)
from networks.models import NetworkIpPool


@task()
def export_ip_numbering_task(ip_pool_id: int, event_time=None):
    pools = NetworkIpPool.objects.filter(pk=ip_pool_id)
    if pools.exists():
        IpNumberingExportTree(event_time=event_time).exportNupload(queryset=pools)


@task()
def export_ip_numbering_stop_using_task(ip_net: str, descr: str,
                                        start_usage_time: datetime,
                                        event_time: datetime):
    IpNumberingStopUsageSimpleExportTree(event_time=event_time).exportNupload(
        ip_net=ip_net,
        descr=descr,
        start_usage_time=start_usage_time,
        event_time=event_time
    )
