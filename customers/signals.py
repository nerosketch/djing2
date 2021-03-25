from datetime import datetime

from django.db.models.signals import post_init, pre_save
from django.dispatch.dispatcher import receiver

from customers.models import CustomerService


@receiver(post_init, sender=CustomerService)
def customer_service_post_init(sender, **kwargs):
    customer_service = kwargs["instance"]
    if getattr(customer_service, "start_time") is None:
        customer_service.start_time = datetime.now()
    if getattr(customer_service, "deadline") is None:
        calc_obj = customer_service.service.get_calc_type()(customer_service)
        customer_service.deadline = calc_obj.calc_deadline()


@receiver(pre_save, sender=CustomerService)
def customer_service_pre_save(sender, **kwargs):
    customer_service = kwargs["instance"]
    if getattr(customer_service, "deadline") is None:
        calc_obj = customer_service.service.get_calc_type()(customer_service)
        customer_service.deadline = calc_obj.calc_deadline()
