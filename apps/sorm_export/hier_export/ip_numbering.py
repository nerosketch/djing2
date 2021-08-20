from typing import Iterable
from datetime import datetime
from sorm_export.hier_export.base import simple_export_decorator, format_fname
from networks.models import NetworkIpPool
from sorm_export.serializers.ip_numbering import IpNumberingExportFormatSerializer


@simple_export_decorator
def export_ip_numbering(pools: Iterable[NetworkIpPool], event_time: datetime):
    """
    В этом файле выгружаются вся IP-нумерация, используемая оператором.
    """
    dat = [{
        'ip_net': net.network,
        # FIXME: формировать описание
        'descr': "Динамические;RADIUS;ШПД;NAT",
        'start_usage_time': event_time,
    } net in pools.iterator()]

    ser = IpNumberingExportFormatSerializer(
        data=dat, many=True
    )
    return ser, f"ISP/dict/ip_numbering_{format_fname(event_time)}.txt"


@simple_export_decorator
def export_ip_numbering_stop_using(ip_net: str, descr: str, start_usage_time: datetime, event_time: datetime):
    """
    В этом файле выгружаются вся IP-нумерация, используемая оператором.
    Вызывается при удалении подсети.
    """
    dat = [{
        'ip_net': ip_net,
        'descr': descr,
        'start_usage_time': start_usage_time,
        'end_usage_time': event_time
    }]

    ser = IpNumberingExportFormatSerializer(
        data=dat, many=True
    )
    return ser, f"ISP/dict/ip_numbering_{format_fname(event_time)}.txt"
