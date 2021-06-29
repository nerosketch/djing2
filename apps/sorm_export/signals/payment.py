from datetime import datetime

from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver

from fin_app.models import AllTimePayLog
from sorm_export.tasks.payment import export_customer_payment_task


@receiver(post_save, sender=AllTimePayLog)
def alltime_payment_signal(sender, instance, created=False, *args, **kwargs):
    # print('signal customer_payment_signal', created, args, kwargs)

    if created:
        export_customer_payment_task(
            pay_log_id_list=[instance.pk],
            event_time=str(datetime.now())
        )
