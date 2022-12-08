from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver
from djing2.lib.ws_connector import send_data2ws, WsEventTypeEnum
from customers.models import Customer


@receiver(post_save, sender=Customer)
def customer_post_save_signal(sender, instance, created=False, **kwargs):
    if not created:
        send_data2ws({
            "eventType": WsEventTypeEnum.UPDATE_CUSTOMER.value,
            "data": {"customer_id": instance.pk}
        })
