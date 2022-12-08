"""Radius application signals file."""
from django.dispatch.dispatcher import receiver

from networks import tasks
from networks.models import CustomerIpLeaseModel
from services import custom_signals as customer_custom_signals
from radiusapp.vendor_base import SpeedInfoStruct, IVendorSpecific
from services.models import CustomerService


@receiver(customer_custom_signals.customer_service_post_pick, sender=CustomerService)
def customer_post_pick_service_signal_handler(sender, instance: CustomerService, service, **kwargs):
    """When single customer picked a service, then change it session to inet.

    :param sender: services.CustomerService class
    :param instance: services.CustomerService instance
    :param service: instance of services.Service.
    """

    # TODO: Duplicate code with: radius_app.views:708
    speed = SpeedInfoStruct(
        speed_in=float(service.speed_in),
        speed_out=float(service.speed_out),
        burst_in=float(service.speed_burst),
        burst_out=float(service.speed_burst),
    )
    speed = IVendorSpecific.get_speed(speed=speed)

    leases = CustomerIpLeaseModel.objects.filter(
        customer=instance.customer,
        state=True
    ).exclude(radius_username=None)
    for lease in leases:
        tasks.async_change_session_guest2inet.delay(
            radius_uname=str(lease.radius_username),
            speed_in=int(speed.speed_in),
            speed_out=int(speed.speed_out),
            speed_in_burst=int(speed.burst_in),
            speed_out_burst=int(speed.burst_out)
        )
