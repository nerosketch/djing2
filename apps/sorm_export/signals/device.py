from datetime import datetime
from django.dispatch.dispatcher import receiver
from django.db.models.signals import post_delete, post_save
from devices.models import Device
from sorm_export.models import CommunicationStandardChoices
from sorm_export.serializers.devices import DeviceSwitchTypeChoices
from sorm_export.tasks.device import (
    send_device_on_delete_task,
    send_device_update_task
)


@receiver(post_delete, sender=Device)
def on_delete_device(sender, instance: Device, *args, **kwargs):
    if instance.address:
        send_device_on_delete_task.delay(
            device_id=instance.pk,
            switch_type=DeviceSwitchTypeChoices.INTERNAL.value,        # TODO: change this hard coding
            network_type=CommunicationStandardChoices.ETHERNET.value,  # TODO: change this hard coding
            descr=instance.comment,
            place=instance.address.full_title(),
            start_usage_time=instance.create_time.timestamp(),
            event_time=datetime.now().timestamp()
        )


@receiver(post_save, sender=Device)
def on_update_device(sender, instance=Device, created=False, *args, **kwargs):
    if instance.address:
        send_device_update_task.delay(
            device_id=int(instance.pk),
            event_time=datetime.now().timestamp()
        )
