from datetime import datetime

from django.db.models.signals import post_save, post_delete
from django.dispatch.dispatcher import receiver

from fin_app.models import AllTimePayLog
from sorm_export.tasks.payment import export_customer_payment_task


@receiver(post_delete, sender=AllTimePayLog)
def customer_payment_signal(sender, instance=None, *args, **kwargs):
    print('signal customer_payment_signal', args, kwargs)

    export_customer_payment_task(
        customer_lease_id_list=[instance.pk],
        event_time=str(datetime.now())
    )
