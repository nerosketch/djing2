from datetime import datetime
from sorm_export.hier_export.base import format_fname, ExportTree, SimpleExportTree
from devices.models import Device
from sorm_export.serializers.devices import DeviceSwitchExportFormat, DeviceSwitchTypeChoices
from sorm_export.models import CommunicationStandardChoices


class DeviceExportTree(ExportTree[Device]):
    """В этом файле выгружаются все коммутаторы, установленные у оператора связи."""

    @staticmethod
    def _calc_switch_type(device: Device):
        # TODO: calc it
        return DeviceSwitchTypeChoices.INTERNAL

    @staticmethod
    def _calc_net_type(device: Device):
        # TODO: calc it
        return CommunicationStandardChoices.ETHERNET.label

    def get_remote_ftp_file_name(self):
        return f'ISP/abonents/switches_{format_fname(self._event_time)}.txt'

    def get_export_format_serializer(self):
        return DeviceSwitchExportFormat

    def get_item(self, device, *args, **kwargs):
        addr = device.address
        if not addr:
            return
        return {
            'title': "switch_%d" % device.pk,
            'switch_type': self._calc_switch_type(device),
            'network_type': self._calc_net_type(device),
            'description': device.comment,
            'place': addr.full_title(),
            'start_usage_time': device.create_time,
        }


class DeviceFinishServeSimpleExportTree(SimpleExportTree):
    def get_remote_ftp_file_name(self):
        return f'ISP/abonents/switches_{format_fname(self._event_time)}.txt'

    def export(self, dev_id: int, switch_type: DeviceSwitchTypeChoices,
               network_type: CommunicationStandardChoices,
               descr: str, place: str, start_usage_time: datetime,
               event_time: datetime, *args, **kwargs):
        dat = [{
            'title': "switch_%d" % dev_id,
            'switch_type': switch_type,
            'network_type': network_type.label,
            'description': descr,
            'place': place,
            'start_usage_time': start_usage_time,
            'end_usage_time': event_time,
        }]

        ser = DeviceSwitchExportFormat(
            data=dat, many=True
        )
        ser.is_valid(raise_exception=True)
        return ser.data
