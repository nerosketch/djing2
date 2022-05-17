from datetime import datetime
from sorm_export.hier_export.base import SimpleExportTree, format_fname, ExportTree
from networks.models import NetworkIpPool
from sorm_export.serializers.ip_numbering import IpNumberingExportFormatSerializer


def make_ip_numbering_description(pool: NetworkIpPool) -> str:
    if pool.is_dynamic:
        return "Динамические;ШПД"
    return "Статические;ШПД"


class IpNumberingExportTree(ExportTree[NetworkIpPool]):
    """
    В этом файле выгружаются вся IP-нумерация, используемая оператором.
    """
    def get_remote_ftp_file_name(self):
        return f"ISP/dict/ip_numbering_{format_fname(self._event_time)}.txt"

    def get_export_format_serializer(self):
        return IpNumberingExportFormatSerializer

    def get_item(self, pool: NetworkIpPool, *args, **kwargs):
        return {
            'ip_net': pool.network,
            'descr': make_ip_numbering_description(pool),
            'start_usage_time': pool.create_time,
        }


class IpNumberingStopUsageSimpleExportTree(SimpleExportTree):
    """
    В этом файле выгружаются вся IP-нумерация, используемая оператором.
    Вызывается при удалении подсети.
    """
    def get_remote_ftp_file_name(self):
        return f"ISP/dict/ip_numbering_{format_fname(self._event_time)}.txt"

    def export(self, ip_net: str, descr: str, start_usage_time: datetime, event_time: datetime, *args, **kwargs):
        dat = [{
            'ip_net': ip_net,
            'descr': descr,
            'start_usage_time': start_usage_time,
            'end_usage_time': event_time
        }]

        ser = IpNumberingExportFormatSerializer(
            data=dat, many=True
        )
        ser.is_valid(raise_exception=True)
        return ser.data
