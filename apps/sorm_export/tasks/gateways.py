from datetime import datetime
from typing import Optional

from djing2 import celery_app
from gateways.models import Gateway
from sorm_export.hier_export.gateways import GatewayStopUsingSimpleExportTree, GatewayExportTree


@celery_app.task
def export_gateway_task(gw_id: int, event_time: Optional[float] = None):
    if event_time is not None:
        event_time = datetime.fromtimestamp(event_time)
    gws = Gateway.objects.filter(pk=gw_id).exclude(place=None)
    GatewayExportTree(event_time=event_time).exportNupload(queryset=gws)


@celery_app.task
def export_gateway_stop_using_task(gw_id: int, gw_type: str, descr: str, gw_place: str, start_use_time: float,
                                   ip_addr: str, ip_port: int, event_time: Optional[float] = None):
    if event_time is not None:
        event_time = datetime.fromtimestamp(event_time)
    start_use_time = datetime.fromtimestamp(start_use_time)
    GatewayStopUsingSimpleExportTree(event_time=event_time).exportNupload(
        gw_id=gw_id,
        gw_type=gw_type,
        descr=descr,
        gw_place=gw_place,
        start_use_time=start_use_time,
        ip_addr=ip_addr,
        ip_port=ip_port,
        event_time=event_time,
    )
