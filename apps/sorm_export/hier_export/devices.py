from typing import Iterable
from sorm_export.hier_export.base import simple_export_decorator, format_fname
from devices.models import Device
from sorm_export.serializers import DeviceSwitchExportFormat, DeviceSwitchTypeChoices
from sorm_export.models import CommunicationStandardChoices


@simple_export_decorator
def export_ip_leases(devices: Iterable[Device], event_time=None):
    """В этом файле выгружаются все коммутаторы, установленные у оператора связи."""

    def _calc_switch_type(device):
        return DeviceSwitchTypeChoices.INTERNAL

    def _calc_net_type(device):
        return CommunicationStandardChoices.ETHERNET

    dat = [{
        'title': "sw_%d" % device.pk,
        'switch_type': _calc_switch_type(device),
        'network_type': _calc_net_type(device),
        'description': device.comment,
        'place': device.comment,
        остановился тут
        'start_usage_time': 'HZ'
    } for device in devices]

    ser = DeviceSwitchExportFormat(
        data=dat, many=True
    )
    return ser, f'ISP/abonents/ip_nets_v1_{format_fname(event_time)}.txt'
