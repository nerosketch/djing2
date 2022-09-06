from datetime import datetime
from typing import Optional

from djing2 import celery_app
from devices.models import Device
from sorm_export.hier_export.devices import (
    DeviceExportTree,
    DeviceFinishServeSimpleExportTree
)
from sorm_export.models import CommunicationStandardChoices
from sorm_export.serializers.devices import DeviceSwitchTypeChoices


@celery_app.task
def send_device_on_delete_task(device_id: int,
                               switch_type: int,
                               network_type: int,
                               descr: str, place: str, start_usage_time: float,
                               event_time: Optional[float] = None):
    if event_time is not None:
        event_time = datetime.fromtimestamp(event_time)
    start_usage_time = datetime.fromtimestamp(start_usage_time)
    switch_type = DeviceSwitchTypeChoices(switch_type)
    network_type = CommunicationStandardChoices(network_type)
    DeviceFinishServeSimpleExportTree(event_time=event_time).exportNupload(
        dev_id=device_id,
        switch_type=switch_type,
        network_type=network_type,
        descr=descr,
        place=place,
        start_usage_time=start_usage_time,
        event_time=event_time,
    )


@celery_app.task
def send_device_update_task(device_id: int, event_time: Optional[float] = None):
    if event_time is not None:
        event_time = datetime.fromtimestamp(event_time)
    dev_qs = Device.objects.filter(pk=device_id)
    if dev_qs.exists():
        DeviceExportTree(event_time=event_time).exportNupload(queryset=dev_qs)
