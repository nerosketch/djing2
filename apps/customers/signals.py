from datetime import datetime

from django.db.models.signals import post_init, pre_save, post_save
from django.dispatch.dispatcher import receiver
from djing2.lib.ws_connector import send_data2ws, WsEventTypeEnum
from customers.models import CustomerService, Customer


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


@receiver(post_save, sender=Customer)
def customer_post_save_signal(sender, instance, created=False, **kwargs):
    if not created:
        send_data2ws({"eventType": WsEventTypeEnum.UPDATE_CUSTOMER.value, "data": {"customer_id": instance.pk}})
