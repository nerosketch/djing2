from datetime import datetime
from uwsgi_tasks import task
from devices.models import Device
from sorm_export.tasks.task_export import task_export
from sorm_export.hier_export.devices import (
    export_devices,
    export_device_finish_serve,
)
from sorm_export.models import CommunicationStandardChoices, ExportStampTypeEnum
from sorm_export.serializers.devices import DeviceSwitchTypeChoices


@task()
def send_device_on_delete_task(device_id: int,
                               switch_type: DeviceSwitchTypeChoices,
                               network_type: CommunicationStandardChoices,
                               descr: str, place: str, start_usage_time: datetime,
                               event_time=None):
    data, fname = export_device_finish_serve(
        dev_id=device_id,
        switch_type=switch_type,
        network_type=network_type,
        descr=descr,
        place=place,
        start_usage_time=start_usage_time,
        event_time=event_time,
    )
    task_export(
        data=data,
        filename=fname,
        export_type=ExportStampTypeEnum.DEVICE_SWITCH
    )


@task()
def send_device_update_task(device_id: int, event_time=None):
    dev_qs = Device.objects.filter(pk=device_id)
    if dev_qs.exists():
        data, fname = export_devices(
            event_time=event_time,
            devices=dev_qs,
        )
        task_export(
            data=data,
            filename=fname,
            export_type=ExportStampTypeEnum.DEVICE_SWITCH
        )
