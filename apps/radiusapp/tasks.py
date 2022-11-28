from customers.models import Customer
from djing2 import celery_app
from djing2.lib.logger import logger
from networks import tasks
from radiusapp.vendor_base import SpeedInfoStruct, IVendorSpecific


@celery_app.task
def check_and_control_session_task(bras_service_name: str, customer_id: int, radius_username: str):
    # Check for service synchronization

    customer = Customer.objects.get(pk=customer_id)

    if 'SERVICE-INET' in bras_service_name:
        # bras contain inet session
        if not customer.is_access():
            logger.info("COA: inet->guest uname=%s" % radius_username)
            tasks.async_change_session_inet2guest(
                radius_uname=radius_username
            )
    elif 'SERVICE-GUEST' in bras_service_name:
        # bras contain guest session
        # TODO: optimize
        if customer.is_access():
            logger.info("COA: guest->inet uname=%s" % radius_username)
            customer_service = customer.active_service()
            service = customer_service.service
            speed = SpeedInfoStruct(
                speed_in=float(service.speed_in),
                speed_out=float(service.speed_out),
                burst_in=float(service.speed_burst),
                burst_out=float(service.speed_burst),
            )
            speed = IVendorSpecific.get_speed(speed=speed)
            tasks.async_change_session_guest2inet(
                radius_uname=radius_username,
                speed_in=int(speed.speed_in),
                speed_out=int(speed.speed_out),
                speed_in_burst=int(speed.burst_in),
                speed_out_burst=int(speed.burst_out)
            )
    tasks.check_if_lease_have_id_db_task(
        radius_uname=radius_username
    )
