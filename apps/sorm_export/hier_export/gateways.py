from typing import Iterable
from datetime import datetime
from gateways.models import Gateway
from sorm_export.hier_export.base import iterable_export_decorator, simple_export_decorator, format_fname
from sorm_export.serializers.gateways import GatewayExportFormatSerializer


@iterable_export_decorator
def export_gateways(gateways_qs: Iterable[Gateway], event_time: datetime):
    """
    В этом файле выгружаются все шлюзы, используемые оператором связи.
    """
    def _gen(gw: Gateway):
        return {
            'gw_id': gw.pk,
            'gw_type': gw.get_gw_class_display(),
            'descr': gw.title,
            'gw_addr': gw.place,
            'start_use_time': gw.create_time,
            # 'deactivate_time':
            'ip_addrs': "%s:%d" % (gw.ip_address, gw.ip_port)
        }
    return (GatewayExportFormatSerializer, _gen, gateways_qs,
            f"ISP/dict/gateways_v1_{format_fname(event_time)}.txt")


@simple_export_decorator
def export_gateway_stop_using(gw_id: int, gw_type: str, descr: str, gw_place: str, start_use_time: datetime,
                              ip_addr: str, ip_port: int, event_time: datetime):
    """
    В этом файле выгружаются все шлюзы, используемые оператором связи.
    """
    dat = [{
        'gw_id': gw_id,
        'gw_type': gw_type,
        'descr': descr,
        'gw_addr': gw_place,
        'start_use_time': start_use_time,
        'deactivate_time': event_time,
        'ip_addrs': "%s:%d" % (ip_addr, ip_port)
    }]
    ser = GatewayExportFormatSerializer(data=dat, many=True)
    return ser, f"ISP/dict/gateways_v1_{format_fname(event_time)}.txt"
