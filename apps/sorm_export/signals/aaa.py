from typing import Type, Optional
from datetime import datetime

from customers.models import Customer
from netaddr import EUI
from netfields.mac import mac_unix_common
from radiusapp import custom_signals
from networks.models import CustomerIpLeaseModel
from django.dispatch.dispatcher import receiver
from djing2.lib import time2utctime
from djing2.lib.logger import logger
from radiusapp.vendors import IVendorSpecific
from radiusapp.vendor_base import RadiusCounters
from sorm_export.serializers.aaa import AAAExportSerializer, AAAEventType
from sorm_export.tasks.aaa import save_radius_acct


def _save_aaa_log(event_time: datetime, **serializer_keys):
    serializer_keys.update({
        "event_time": time2utctime(event_time),
    })
    ser = AAAExportSerializer(
        data=serializer_keys
    )
    ser.is_valid(raise_exception=True)
    return save_radius_acct(
        data=ser.data
    )


@receiver(custom_signals.radius_acct_start_signal, sender=CustomerIpLeaseModel)
def signal_radius_session_acc_start(
    sender,
    instance: CustomerIpLeaseModel,
    data: dict,
    ip_addr: str,
    customer,
    radius_unique_id: str,
    event_time: datetime,
    customer_mac: EUI,
    *args,
    **kwargs
):
    nas_port = IVendorSpecific.get_rad_val(data, "NAS-Port", int, 0)

    customer_username = customer.username

    _save_aaa_log(
        event_time=event_time,
        event_type=AAAEventType.RADIUS_AUTH_START,
        session_id=radius_unique_id,
        customer_ip=ip_addr,
        customer_db_username=customer_username,
        nas_port=nas_port,
        customer_device_mac=customer_mac.format(dialect=mac_unix_common) if customer_mac else ''
    )


@receiver(custom_signals.radius_acct_stop_signal, sender=CustomerIpLeaseModel)
def signal_radius_session_acct_stop(
        sender: Type[CustomerIpLeaseModel],
        instance: CustomerIpLeaseModel,
        data: dict,
        counters: RadiusCounters,
        ip_addr: str,
        customer: Customer,
        radius_unique_id: str, customer_mac: EUI,
        *args, **kwargs):

    event_time = datetime.now()

    nas_port = IVendorSpecific.get_rad_val(data, "NAS-Port", int, 0)

    try:
        _save_aaa_log(
            event_time=event_time,
            event_type=AAAEventType.RADIUS_AUTH_STOP,
            session_id=radius_unique_id,
            customer_ip=ip_addr,
            customer_db_username=customer.username,
            nas_port=nas_port,
            customer_device_mac=customer_mac.format(dialect=mac_unix_common) if customer_mac else '',
            input_octets=counters.input_octets,
            output_octets=counters.output_octets,
        )
    except Exception as err:
        logger.error("signal_radius_session_acct_stop: Error export AAA: %s" % err)


@receiver(custom_signals.radius_auth_update_signal, sender=CustomerIpLeaseModel)
def signal_radius_acct_update(
        sender: Type[CustomerIpLeaseModel],
        instance: Optional[CustomerIpLeaseModel],
        data: dict,
        counters: RadiusCounters,
        radius_unique_id: str,
        ip_addr: str,
        customer_mac: EUI,
        customer: Customer,
        *args, **kwargs):

    nas_port = IVendorSpecific.get_rad_val(data, "NAS-Port", int, 0)

    event_time = datetime.now()
    _save_aaa_log(
        event_time=event_time,
        event_type=AAAEventType.RADIUS_AUTH_UPDATE,
        session_id=radius_unique_id,
        customer_ip=ip_addr,
        customer_db_username=customer.username,
        nas_port=nas_port,
        customer_device_mac=customer_mac.format(dialect=mac_unix_common) if customer_mac else '',
        input_octets=counters.input_octets,
        output_octets=counters.output_octets,
    )
