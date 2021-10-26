from datetime import datetime
from typing import Iterable
from sorm_export.hier_export.base import iterable_export_decorator, simple_export_decorator, format_fname
from devices.models import Device
from sorm_export.serializers.devices import DeviceSwitchExportFormat, DeviceSwitchTypeChoices
from sorm_export.models import CommunicationStandardChoices


@iterable_export_decorator
def export_devices(devices: Iterable[Device], event_time: datetime):
    """В этом файле выгружаются все коммутаторы, установленные у оператора связи."""

    def _calc_switch_type(device: Device):
        # TODO: calc it
        return DeviceSwitchTypeChoices.INTERNAL

    def _calc_net_type(device: Device):
        # TODO: calc it
        return CommunicationStandardChoices.ETHERNET.label

    def _gen(device: Device):
        addr = device.address
        if not addr:
            return
        return {
            'title': "switch_%d" % device.pk,
            'switch_type': _calc_switch_type(device),
            'network_type': _calc_net_type(device),
            'description': device.comment,
            'place': addr.full_title(),
            'start_usage_time': device.create_time,
        }

    return (DeviceSwitchExportFormat, _gen, devices,
            f'ISP/abonents/switches_{format_fname(event_time)}.txt')


@simple_export_decorator
def export_device_finish_serve(dev_id: int, switch_type: DeviceSwitchTypeChoices,
                               network_type: CommunicationStandardChoices,
                               descr: str, place: str, start_usage_time: datetime,
                               event_time: datetime):
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
    return ser, f'ISP/abonents/switches_{format_fname(event_time)}.txt'
