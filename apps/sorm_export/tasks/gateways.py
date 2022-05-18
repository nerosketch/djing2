from datetime import datetime
from uwsgi_tasks import task
from gateways.models import Gateway
from sorm_export.hier_export.gateways import GatewayStopUsingSimpleExportTree, GatewayExportTree


@task()
def export_gateway_task(gw_id: int, event_time=None):
    gws = Gateway.objects.filter(pk=gw_id).exclude(place=None)
    GatewayExportTree(event_time=event_time).exportNupload(queryset=gws)


@task()
def export_gateway_stop_using_task(gw_id: int, gw_type: str, descr: str, gw_place: str, start_use_time: datetime,
                                   ip_addr: str, ip_port: int, event_time: datetime):
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
