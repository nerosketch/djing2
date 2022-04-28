"""Radius application signals file."""
from django.dispatch.dispatcher import receiver

from networks import tasks
from customers import custom_signals as customer_custom_signals
from customers.models import CustomerService


@receiver(
    customer_custom_signals.customer_service_batch_pre_stop,
    sender=CustomerService,
    dispatch_uid="on_pre_batch_stop_customer_services&$@(7",
)
def on_pre_batch_stop_customer_services_signal(sender, expired_services, **kwargs):
    """When a lot of customers picked services, then reset its session.

    :param sender: CustomerService class
    :param expired_services: queryset of CustomerService
    :param kwargs:
    :return: nothing
    """
    for es in expired_services.select_related('customer').iterator():
        uname = es.customer.username
        tasks.async_change_session_inet2guest(radius_uname=uname)

