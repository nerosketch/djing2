from django.dispatch.dispatcher import receiver
from django.db.models.signals import post_delete, post_save

from djing2.lib.ws_connector import send_data2ws, WsEventTypeEnum
from networks.models import CustomerIpLeaseModel


@receiver(post_delete, sender=CustomerIpLeaseModel)
def on_remove_ip_lease_signal(sender, instance, **kwargs):
    send_data2ws(
        {"eventType": WsEventTypeEnum.UPDATE_CUSTOMER_LEASES.value, "data": {"customer_id": instance.customer_id}}
    )


@receiver(post_save, sender=CustomerIpLeaseModel)
def on_post_save_ip_lease_signal(sender, instance, **kwargs):
    send_data2ws(
        {"eventType": WsEventTypeEnum.UPDATE_CUSTOMER_LEASES.value, "data": {"customer_id": instance.customer_id}}
    )
