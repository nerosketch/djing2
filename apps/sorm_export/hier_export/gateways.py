from datetime import datetime
from gateways.models import Gateway
from sorm_export.hier_export.base import format_fname, ExportTree, SimpleExportTree
from sorm_export.serializers.gateways import GatewayExportFormatSerializer
from sorm_export.models import ExportStampTypeEnum


class GatewayExportTree(ExportTree[Gateway]):
    """
    В этом файле выгружаются все шлюзы, используемые оператором связи.
    """
    def get_remote_ftp_file_name(self):
        return f"ISP/dict/gateways_v1_{format_fname(self._event_time)}.txt"

    @classmethod
    def get_export_format_serializer(cls):
        return GatewayExportFormatSerializer

    @classmethod
    def get_export_type(cls):
        return ExportStampTypeEnum.GATEWAYS

    def get_item(self, gw, *args, **kwargs):
        return {
            'gw_id': gw.pk,
            'gw_type': gw.get_gw_class_display(),
            'descr': gw.title,
            'gw_addr': gw.place,
            'start_use_time': gw.create_time,
            # 'deactivate_time':
            'ip_addrs': "%s:%d" % (gw.ip_address, gw.ip_port)
        }


class GatewayStopUsingSimpleExportTree(SimpleExportTree):
    """
    В этом файле выгружаются все шлюзы, используемые оператором связи.
    """
    def get_remote_ftp_file_name(self):
        return f"ISP/dict/gateways_v1_{format_fname(self._event_time)}.txt"

    @classmethod
    def get_export_type(cls):
        return ExportStampTypeEnum.GATEWAYS

    def export(self, gw_id: int, gw_type: str, descr: str, gw_place: str, start_use_time: datetime,
               ip_addr: str, ip_port: int, event_time: datetime, *args, **kwargs):
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
        ser.is_valid(raise_exception=True)
        return ser.data
