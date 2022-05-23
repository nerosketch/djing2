"""Radius application signals file."""
from django.dispatch.dispatcher import receiver
from djing2.lib import LogicError
from rest_framework import status

from networks import tasks
from networks.models import CustomerIpLeaseModel
from customers import custom_signals as customer_custom_signals
from customers.models import CustomerService, Customer
from radiusapp.vendor_base import SpeedInfoStruct, IVendorSpecific


@receiver(
    customer_custom_signals.customer_service_batch_pre_stop,
    sender=CustomerService,
    dispatch_uid="on_pre_batch_stop_customer_services&$@(7",
)
def on_pre_batch_stop_customer_services_signal(sender, instance: CustomerService, expired_services, **kwargs):
    """When a lot of customers picked services, then reset its session.

    :param sender: CustomerService class
    :param expired_services: queryset of CustomerService
    :param kwargs:
    """
    for es in expired_services.select_related('customer').iterator():
        uname = es.customer.username
        tasks.async_change_session_inet2guest(radius_uname=uname)


@receiver(customer_custom_signals.customer_service_post_pick, sender=Customer)
def customer_post_pick_service_signal_handler(sender, instance: Customer, service, **kwargs):
    """When single customer picked a service, then change it session to inet.

    :param sender: customers.Customer class
    :param instance:
    :param service: instance of services.Service.
    """
    if not instance.current_service_id:
        raise LogicError(
            detail="Server error: Customer has not current_service",
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    speed = SpeedInfoStruct(
        speed_in=float(service.speed_in),
        speed_out=float(service.speed_out),
        burst_in=float(service.speed_burst),
        burst_out=float(service.speed_burst),
    )
    speed = IVendorSpecific.get_speed(speed=speed)

    leases = CustomerIpLeaseModel.objects.filter(customer=instance, state=True).exclude(radius_username=None)
    for lease in leases:
        tasks.async_change_session_guest2inet(
            radius_uname=str(lease.radius_username),
            speed_in=speed.speed_in,
            speed_out=speed.speed_out,
            speed_in_burst=speed.burst_in,
            speed_out_burst=speed.burst_out
        )


@receiver(customer_custom_signals.customer_service_post_stop, sender=CustomerService)
def on_customer_stops_service(sender, instance: CustomerService, customer: Customer, **kwargs):
    """When single customer stopped his service, then change it session to guest.

    :param sender: customers.Customer class
    :param instance:
    :param csutomer: instance of customers.Customer
    """
    leases = CustomerIpLeaseModel.objects.filter(customer=customer, state=True).exclude(radius_username=None)
    for lease in leases:
        tasks.async_change_session_inet2guest(
            radius_uname=str(lease.radius_username)
        )

