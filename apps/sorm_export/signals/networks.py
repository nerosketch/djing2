from datetime import datetime
from typing import Optional

from django.db.models.signals import post_save, pre_delete
from django.dispatch.dispatcher import receiver
from networks.models import CustomerIpLeaseModel
from sorm_export.tasks.networks import (
    export_static_ip_leases_task_finish
)


#@receiver(post_save, sender=CustomerIpLeaseModel)
#def customer_ip_changed(sender, instance: Optional[CustomerIpLeaseModel] = None, *args, **kwargs):
#    if not instance.is_dynamic:
#        # only if lease is static
#        # https://wiki.vasexperts.ru/doku.php?id=sorm:sorm3:sorm3_subs_dump:sorm3_subs_ip_nets:start
#        export_static_ip_leases_task(
#            customer_lease_id_list=[instance.pk],
#            event_time=datetime.now()
#        )


@receiver(pre_delete, sender=CustomerIpLeaseModel)
def customer_ip_deleted(sender, instance, *args, **kwargs):
    if not instance.is_dynamic:
        export_static_ip_leases_task_finish.delay(
            customer_id=instance.customer_id,
            ip_address=instance.ip_address,
            lease_time=instance.lease_time,
            mac_address=instance.mac_address,
            event_time=datetime.now()
        )
