"""Radius application signals file."""
from django.dispatch.dispatcher import receiver
from djing2.lib import LogicError
from rest_framework import status

from networks import tasks
from networks.models import CustomerIpLeaseModel
from customers import custom_signals as customer_custom_signals
from customers.models import Customer
from radiusapp.vendor_base import SpeedInfoStruct, IVendorSpecific


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
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # TODO: Duplicate code with: radius_app.views:708
    speed = SpeedInfoStruct(
        speed_in=float(service.speed_in),
        speed_out=float(service.speed_out),
        burst_in=float(service.speed_burst),
        burst_out=float(service.speed_burst),
    )
    speed = IVendorSpecific.get_speed(speed=speed)

    leases = CustomerIpLeaseModel.objects.filter(
        customer=instance,
        state=True
    ).exclude(radius_username=None)
    for lease in leases:
        tasks.async_change_session_guest2inet.delay(
            radius_uname=str(lease.radius_username),
            speed_in=speed.speed_in,
            speed_out=speed.speed_out,
            speed_in_burst=speed.burst_in,
            speed_out_burst=speed.burst_out
        )
