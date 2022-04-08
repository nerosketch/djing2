from datetime import datetime

from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver

from fin_app.models.alltime import AllTimePayLog
from sorm_export.tasks.payment import export_customer_payment_task


@receiver(post_save, sender=AllTimePayLog)
def alltime_payment_signal(sender, instance, created=False, *args, **kwargs):
    if created:
        export_customer_payment_task(
            customer_id=instance.customer_id,
            pay_id=instance.pay_id,
            date_add=instance.date_add,
            summ=instance.sum,
            trade_point=instance.trade_point,
            receipt_num=instance.receipt_num,
            pay_gw=instance.pay_gw,
            event_time=datetime.now()
        )
