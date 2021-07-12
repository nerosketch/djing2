from datetime import datetime
from netaddr import EUI
from netfields.mac import mac_unix_common
from radiusapp import custom_signals
from django.dispatch.dispatcher import receiver
from radiusapp.models import CustomerRadiusSession
from radiusapp.vendors import IVendorSpecific
from sorm_export.serializers.aaa import AAAExportSerializer, AAAEventType
from sorm_export.tasks.aaa import save_radius_acct


def _save_aaa_log(event_time: datetime, **serializer_keys):
    serializer_keys.update({
        "event_time": event_time,
    })
    ser = AAAExportSerializer(
        data=serializer_keys
    )
    ser.is_valid(raise_exception=True)
    return save_radius_acct(event_time=event_time, data=ser.data)


@receiver(custom_signals.radius_auth_start_signal, sender=CustomerRadiusSession)
def signal_radius_session_acc_start(
    sender,
    instance: CustomerRadiusSession,
    data: dict,
    ip_addr: str,
    customer,
    radius_unique_id: str,
    event_time: datetime,
    customer_mac: EUI,
    *args,
    **kwargs
):
    nas_port = IVendorSpecific.get_rad_val(data, "NAS-Port", 0)
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


@receiver(custom_signals.radius_auth_stop_signal, sender=CustomerRadiusSession)
def signal_radius_session_acct_stop(
    sender, instance_queryset, data: dict, ip_addr: str, radius_unique_id: str, customer_mac: EUI, *args, **kwargs
):
    nas_port = IVendorSpecific.get_rad_val(data, "NAS-Port", 0)

    if instance_queryset.exists():
        session = instance_queryset.first()
        if session:
            customer_username = session.customer.username
        else:
            return
    else:
        return

    event_time = datetime.now()

    _save_aaa_log(
        event_time=event_time,
        event_type=AAAEventType.RADIUS_AUTH_STOP,
        session_id=radius_unique_id,
        customer_ip=ip_addr,
        customer_db_username=customer_username,
        nas_port=nas_port,
        customer_device_mac=customer_mac.format(dialect=mac_unix_common) if customer_mac else ''
    )
