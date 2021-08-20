from django.db.models.signals import post_save, pre_delete
from django.dispatch.dispatcher import receiver
from networks.models import NetworkIpPool
from sorm_export.signals.ip_numbering import (
    export_ip_numbering_task,
    export_ip_numbering_stop_using_task
)


@receiver(post_save, sender=NetworkIpPool)
def on_ip_pool_save(sender, instance: NetworkIpPool, *args, **kwargs):
    export_ip_numbering_task(ip_pool_id=instance.pk)


@receiver(post_delete, sender=NetworkIpPool)
def on_ip_pool_delete(sender, instance: NetworkIpPool, *args, **kwargs):
    export_ip_numbering_stop_using_task(
        ip_net=instance.network,
        descr="Динамические;RADIUS;ШПД;NAT",
        start_usage_time='',
    )
