"""Radius application signals file."""
from django.dispatch.dispatcher import receiver
from django.db.models.signals import pre_delete

from djing2.lib import safe_int
from networks.models import CustomerIpLeaseModel
from radiusapp.models import CustomerRadiusSession
from radiusapp import tasks
from customers import custom_signals as customer_custom_signals
from customers.models import Customer, CustomerService


@receiver(pre_delete, sender=CustomerIpLeaseModel)
def try_stop_session_too_signal(sender, instance, **kwargs):
    """
    When ip lease removed then trying to stop session too.

    :param sender: CustomerIpLeaseModel class
    :param instance: CustomerIpLeaseModel instance
    :param kwargs:
    :return: nothing
    """
    sess = CustomerRadiusSession.objects.filter(ip_lease=instance).first()
    if sess:
        sess.finish_session()


@receiver(customer_custom_signals.customer_service_pre_stop,
          sender=CustomerService,
          dispatch_uid='on_pre_stop_cust_srv%&6')
def on_pre_stop_cust_srv_signal(sender, expired_service, **kwargs):
    """
    When customer service has stopped then try to async stop his session too.

    :param sender: CustomerService class
    :param expired_service: CustomerService instance
    :param kwargs:
    :return: nothing
    """
    print('#' * 80)
    print('on_pre_stop_cust_srv')
    print('#' * 80)
    tasks.radius_stop_customer_session_task(
        customer_id=expired_service.customer.pk
    )


@receiver(customer_custom_signals.customer_service_pre_pick,
          sender=Customer, dispatch_uid='on_pre_pick_cust_srv*$@0')
def on_pre_pick_cust_srv_signal(sender, customer, service, **kwargs):
    """
    When customer picked service then reset his session.

    :param sender: Customer class
    :param customer: Customer instance
    :param service: Service instance
    :param kwargs:
    :return: nothing
    """
    print('#' * 80)
    print('on_pre_pick_cust_srv', customer, service)
    print('#' * 80)
    tasks.radius_stop_customer_session_task(
        customer_id=customer.pk
    )


@receiver(customer_custom_signals.customer_service_batch_pre_stop,
          sender=CustomerService,
          dispatch_uid='on_pre_batch_stop_customer_services&$@(7')
def on_pre_batch_stop_customer_services_signal(sender, expired_services,
                                               **kwargs):
    """When a lot of customers picked services, then reset its session.

    :param sender: CustomerService class
    :param expired_services: queryset of CustomerService
    :param kwargs:
    :return: nothing
    """
    print('#' * 80)
    print('on_pre_batch_stop_customer_services_signal', expired_services)
    print('#' * 80)
    customer_ids = (safe_int(es.customer.pk) for es in
                    expired_services.iterator())
    customer_ids = tuple(i for i in customer_ids if i > 0)
    tasks.radius_batch_stop_customer_services_task(
        customer_ids=customer_ids
    )
