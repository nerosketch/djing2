"""Radius application signals file."""
import logging
from django.dispatch.dispatcher import receiver
from django.db.models.signals import pre_delete

from djing2.lib import safe_int
from radiusapp.models import CustomerRadiusSession
from radiusapp import tasks
from customers import custom_signals as customer_custom_signals
from customers.models import Customer, CustomerService
from networks.models import CustomerIpLeaseModel


@receiver(pre_delete, sender=CustomerIpLeaseModel)
def send_finish_session_when_removed_it_ip(sender, instance, **kwargs):
    """
    Try to stop session when removing customer ip lease.
    :param sender: CustomerIpLeaseModel class
    :param instance: CustomerIpLeaseModel instance
    :param kwargs:
    :return: nothing
    """
    sessions = CustomerRadiusSession.objects.filter(ip_lease=instance).only("radius_username")
    for session in sessions:
        tasks.async_finish_session_task(session.radius_username)


@receiver(
    customer_custom_signals.customer_service_pre_stop, sender=CustomerService, dispatch_uid="on_pre_stop_cust_srv%&6"
)
def on_pre_stop_cust_srv_signal(sender, expired_service, **kwargs):
    """
    When customer service has stopped then try to
    change his session from inet to guest.

    :param sender: CustomerService class
    :param expired_service: CustomerService instance
    :param kwargs:
    :return: nothing
    """
    sessions = CustomerRadiusSession.objects.filter(customer_id=expired_service.customer.pk).iterator()
    for session in sessions:
        if tasks.async_change_session_inet2guest(radius_uname=session.radius_username):
            logging.info('Session "%s" changed inet -> guest' % session)
        else:
            logging.error('Session "%s" not changed inet -> guest' % session)


@receiver(customer_custom_signals.customer_service_post_pick, sender=Customer, dispatch_uid="on_pre_pick_cust_srv*$@0")
def on_post_pick_cust_srv_signal(sender, customer, service, **kwargs):
    """
    When customer picked service then reset his session.

    :param sender: Customer class
    :param customer: Customer instance
    :param service: Service instance
    :param kwargs:
    :return: nothing
    """

    speed_in = speed_out = speed_in_burst = speed_out_burst = None
    is_customer_has_service = bool(customer.active_service())
    if is_customer_has_service:
        speed_in = int(service.speed_in * 1000000)
        speed_out = int(service.speed_out * 1000000)
        speed_in_burst, speed_out_burst = service.calc_burst()

    sessions = CustomerRadiusSession.objects.filter(customer_id=customer.pk).only("radius_username").iterator()
    for session in sessions:
        if is_customer_has_service:
            # change radius session guest->inet

            tasks.async_change_session_guest2inet(
                radius_uname=session.radius_username,
                speed_in=speed_in,
                speed_out=speed_out,
                speed_in_burst=speed_in_burst,
                speed_out_burst=speed_out_burst,
            )
        else:
            # change radius session inet->guest
            tasks.async_change_session_inet2guest(
                radius_uname=session.radius_username,
            )


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
    customer_ids = (safe_int(es.customer.pk) for es in expired_services.iterator())
    customer_ids = tuple(i for i in customer_ids if i > 0)
    tasks.radius_batch_stop_customer_services_task(customer_ids=customer_ids)
