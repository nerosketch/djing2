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
    if instance.place:
        send_device_on_delete_task(
            device_id=instance.pk,
            switch_type=DeviceSwitchTypeChoices.INTERNAL,        # TODO: change this hard coding
            network_type=CommunicationStandardChoices.ETHERNET,  # TODO: change this hard coding
            descr=instance.comment,
            place=instance.place,
            start_usage_time=instance.create_time,
            event_time=datetime.now()
        )


@receiver(post_save, sender=Device)
def on_update_device(sender, instance=Device, created=False, *args, **kwargs):
    send_device_update_task(
        device_id=int(instance.pk),
        event_time=datetime.now()
    )
