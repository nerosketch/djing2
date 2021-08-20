from datetime import datetime
from django.db.models.signals import post_save, post_delete
from django.dispatch.dispatcher import receiver
from networks.models import NetworkIpPool
from sorm_export.hier_export.ip_numbering import make_ip_numbering_description
from sorm_export.tasks.ip_numbering import (
    export_ip_numbering_task,
    export_ip_numbering_stop_using_task
)


@receiver(post_save, sender=NetworkIpPool)
def on_ip_pool_save(sender, instance: NetworkIpPool, *args, **kwargs):
    export_ip_numbering_task(ip_pool_id=instance.pk, event_time=datetime.now())


@receiver(post_delete, sender=NetworkIpPool)
def on_ip_pool_delete(sender, instance: NetworkIpPool, *args, **kwargs):
    export_ip_numbering_stop_using_task(
        ip_net=instance.network,
        descr=make_ip_numbering_description(instance),
        start_usage_time=instance.create_time,
        event_time=datetime.now()
    )
