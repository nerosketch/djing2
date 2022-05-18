from datetime import datetime
from uwsgi_tasks import task
from devices.models import Device
from sorm_export.hier_export.devices import (
    DeviceExportTree,
    DeviceFinishServeSimpleExportTree
)
from sorm_export.models import CommunicationStandardChoices
from sorm_export.serializers.devices import DeviceSwitchTypeChoices


@task()
def send_device_on_delete_task(device_id: int,
                               switch_type: DeviceSwitchTypeChoices,
                               network_type: CommunicationStandardChoices,
                               descr: str, place: str, start_usage_time: datetime,
                               event_time=None):
    DeviceFinishServeSimpleExportTree(event_time=event_time).exportNupload(
        dev_id=device_id,
        switch_type=switch_type,
        network_type=network_type,
        descr=descr,
        place=place,
        start_usage_time=start_usage_time,
        event_time=event_time,
    )


@task()
def send_device_update_task(device_id: int, event_time=None):
    dev_qs = Device.objects.filter(pk=device_id)
    if dev_qs.exists():
        DeviceExportTree(event_time=event_time).exportNupload(queryset=dev_qs)
