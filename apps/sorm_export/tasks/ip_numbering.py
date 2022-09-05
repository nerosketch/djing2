from datetime import datetime
from typing import Optional

from djing2 import celery_app
from sorm_export.hier_export.ip_numbering import (
    IpNumberingStopUsageSimpleExportTree,
    IpNumberingExportTree
)
from networks.models import NetworkIpPool


@celery_app.task
def export_ip_numbering_task(ip_pool_id: int, event_time: Optional[float] = None):
    if event_time is not None:
        event_time = datetime.fromtimestamp(event_time)
    pools = NetworkIpPool.objects.filter(pk=ip_pool_id)
    if pools.exists():
        IpNumberingExportTree(event_time=event_time).exportNupload(queryset=pools)


@celery_app.task
def export_ip_numbering_stop_using_task(ip_net: str, descr: str,
                                        start_usage_time: float,
                                        event_time: Optional[float] = None):
    if event_time is not None:
        event_time = datetime.fromtimestamp(event_time)
    start_usage_time = datetime.fromtimestamp(start_usage_time)
    IpNumberingStopUsageSimpleExportTree(event_time=event_time).exportNupload(
        ip_net=ip_net,
        descr=descr,
        start_usage_time=start_usage_time,
        event_time=event_time
    )
