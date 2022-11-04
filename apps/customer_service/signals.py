from datetime import datetime
from django.db.models.signals import post_init, pre_save
from django.dispatch.dispatcher import receiver
from customer_service.models import CustomerService


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
