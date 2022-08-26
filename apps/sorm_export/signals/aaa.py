from typing import Type, Optional
from datetime import datetime

from django.core.mail import send_mail
from netaddr import EUI
from netfields.mac import mac_unix_common
from radiusapp import custom_signals
from networks.models import CustomerIpLeaseModel
from django.conf import settings
from django.dispatch.dispatcher import receiver
from djing2.lib import time2utctime
from djing2.lib.logger import logger
from radiusapp.vendors import IVendorSpecific
from radiusapp.vendor_base import RadiusCounters
from rest_framework.exceptions import ValidationError
from sorm_export.serializers.aaa import AAAExportSerializer, AAAEventType
from sorm_export.tasks.aaa import save_radius_acct


def _save_aaa_log(event_time: datetime, **serializer_keys):
    serializer_keys.update({
        "event_time": time2utctime(event_time),
    })
    try:
        ser = AAAExportSerializer(
            data=serializer_keys
        )
        ser.is_valid(raise_exception=True)
        return save_radius_acct.delay(event_time=event_time, data=ser.data)
    except ValidationError as err:
        sorm_reporting_emails = getattr(settings, 'SORM_REPORTING_EMAILS', None)
        if sorm_reporting_emails is not None:
            send_mail(
                'AAA export log error',
                str(err),
                getattr(settings, 'DEFAULT_FROM_EMAIL'),
                sorm_reporting_emails
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
        instance_queryset, data: dict,
        counters: RadiusCounters,
        ip_addr: str,
        radius_unique_id: str, customer_mac: EUI,
        *args, **kwargs):
    nas_port = IVendorSpecific.get_rad_val(data, "NAS-Port", int, 0)

    # TODO: Optimize
    if instance_queryset.exists():
        session = instance_queryset.first()
        if session and session.customer:
            customer_username = session.customer.username
        else:
            return
    else:
        return

    event_time = datetime.now()

    try:
        _save_aaa_log(
            event_time=event_time,
            event_type=AAAEventType.RADIUS_AUTH_STOP,
            session_id=radius_unique_id,
            customer_ip=ip_addr,
            customer_db_username=customer_username,
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
        instance_queryset,
        data: dict,
        counters: RadiusCounters,
        radius_unique_id: str,
        ip_addr: str,
        customer_mac: EUI,
        *args, **kwargs):

    nas_port = IVendorSpecific.get_rad_val(data, "NAS-Port", int, 0)

    # TODO: Optimize
    if instance_queryset.exists():
        session = instance_queryset.first()
        if session and session.customer:
            customer_username = session.customer.username
        else:
            return
    else:
        return

    event_time = datetime.now()
    _save_aaa_log(
        event_time=event_time,
        event_type=AAAEventType.RADIUS_AUTH_UPDATE,
        session_id=radius_unique_id,
        customer_ip=ip_addr,
        customer_db_username=customer_username,
        nas_port=nas_port,
        customer_device_mac=customer_mac.format(dialect=mac_unix_common) if customer_mac else '',
        input_octets=counters.input_octets,
        output_octets=counters.output_octets,
    )

