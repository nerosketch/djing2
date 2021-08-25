from datetime import datetime
from django.db.models.signals import post_save, post_delete
from django.dispatch.dispatcher import receiver
from gateways.models import Gateway
from sorm_export.tasks.gateways import export_gateway_task, export_gateway_stop_using_task


@receiver(post_save, sender=Gateway)
def on_gateway_save(sender, instance: Gateway, *args, **kwargs):
    if not instance.place:
        return
    export_gateway_task(
        gw_id=instance.pk,
        event_time=datetime.now(),
    )


@receiver(post_delete, sender=Gateway)
def on_gateway_delete(sender, instance: Gateway, *args, **kwargs):
    if not instance.place:
        return
    export_gateway_stop_using_task(
        gw_id=instance.pk,
        gw_type=instance.get_gw_class_display(),
        descr=instance.title,
        gw_place=instance.place,
        start_use_time=instance.create_time,
        ip_addr=instance.ip_address,
        ip_port=instance.ip_port,
        event_time=datetime.now()
    )
