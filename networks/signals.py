from django.dispatch.dispatcher import receiver
from django.db.models.signals import pre_delete, post_init

from djing2.lib.ws_connector import send_data2ws, WsEventTypeEnum
from networks.models import CustomerIpLeaseModel


@receiver(pre_delete, sender=CustomerIpLeaseModel)
def on_remove_ip_lease_signal(sender, instance, **kwargs):
    send_data2ws({
        'eventType': WsEventTypeEnum.UPDATE_CUSTOMER_LEASES.value,
        'data': {
            'customer_id': instance.customer_id
        }
    })


@receiver(post_init, sender=CustomerIpLeaseModel)
def on_init_ip_lease_signal(sender, instance, **kwargs):
    send_data2ws({
        'eventType': WsEventTypeEnum.UPDATE_CUSTOMER_LEASES.value,
        'data': {
            'customer_id': instance.customer_id
        }
    })
