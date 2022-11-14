from datetime import datetime

from django.db.models.signals import post_save, pre_delete
from django.dispatch.dispatcher import receiver
from networks.models import CustomerIpLeaseModel
from sorm_export.tasks.networks import (
    export_static_ip_leases_task_finish
)


@receiver(pre_delete, sender=CustomerIpLeaseModel)
def customer_ip_deleted(sender, instance, *args, **kwargs):
    if not instance.is_dynamic:
        export_static_ip_leases_task_finish.delay(
            customer_id=instance.customer_id,
            ip_address=str(instance.ip_address),
            lease_time=instance.lease_time.timestamp(),
            mac_address=str(instance.mac_address),
            event_time=datetime.now().timestamp()
        )
