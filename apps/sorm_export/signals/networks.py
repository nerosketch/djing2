from datetime import datetime
from typing import Optional

from django.db.models.signals import post_save, post_delete
from django.dispatch.dispatcher import receiver
from networks.models import CustomerIpLeaseModel
from sorm_export.tasks.networks import export_ip_leases_task


@receiver(post_save, sender=CustomerIpLeaseModel)
def customer_ip_changed(sender, instance: Optional[CustomerIpLeaseModel] = None, *args, **kwargs):
    if not instance.is_dynamic:
        # only if lease is static
        # https://wiki.vasexperts.ru/doku.php?id=sorm:sorm3:sorm3_subs_dump:sorm3_subs_ip_nets:start
        export_ip_leases_task(
            customer_lease_id_list=[instance.pk],
            event_time=str(datetime.now())
        )


@receiver(post_delete, sender=CustomerIpLeaseModel)
def customer_ip_deleted(sender, *args, **kwargs):
    print('signal customer_ip_deleted', args, kwargs)
    # TODO: узнать можно-ли удалять ip
