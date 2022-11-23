from datetime import datetime
from django.db.models.signals import post_init, pre_save
from django.dispatch.dispatcher import receiver
from services.custom_signals import customer_service_post_pick
from services.models import CustomerService, CustomerServiceConnectingQueueModel


@receiver(post_init, sender=CustomerService)
def customer_service_post_init(sender, instance: CustomerService, **kwargs):
    customer_service = instance
    if getattr(customer_service, "start_time") is None:
        customer_service.start_time = datetime.now()
    if getattr(customer_service, "deadline") is None:
        customer_service.assign_deadline()


@receiver(pre_save, sender=CustomerService)
def customer_service_pre_save(sender, instance: CustomerService, **kwargs):
    customer_service = instance
    if getattr(customer_service, "deadline") is None:
        customer_service.assign_deadline()


@receiver(customer_service_post_pick, sender=CustomerService)
def on_connect_new_service_update_first_item_in_queue(sender, instance: CustomerService, **kwargs):
    CustomerServiceConnectingQueueModel.objects.filter(
        customer_id=instance.customer_id
    ).replace_first(
        service_id=instance.service_id
    )
