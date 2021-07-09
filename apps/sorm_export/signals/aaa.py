from datetime import datetime
from json import dump
from radiusapp import custom_signals
from django.dispatch.dispatcher import receiver
from radiusapp.models import CustomerRadiusSession
from radiusapp.vendors import IVendorSpecific
from sorm_export.serializers.aaa import AAAExportSerializer, AAAEventType
from sorm_export.tasks.aaa import save_radius_acct


@receiver(custom_signals.radius_auth_start_signal, sender=CustomerRadiusSession)
def signal_radius_session_acc_start(
    sender,
    instance: CustomerRadiusSession,
    data: dict,
    ip_addr: str,
    radius_username: str,
    customer_ip_lease,
    customer,
    radius_unique_id: str,
    event_time: datetime,
    customer_mac: str,
    *args,
    **kwargs
):

    with open("/tmp/radius_start.log", "a") as f:
        dump(data, f)
        f.write("\n")

    nas_port = IVendorSpecific.get_rad_val(data, "NAS-Port", 0)

    customer_username = customer.username

    ser = AAAExportSerializer(
        data={
            "event_time": event_time,
            "event_type": AAAEventType.RADIUS_AUTH_START,
            "session_id": radius_unique_id,
            "customer_ip": customer_ip_lease,
            "customer_db_username": customer_username,
            # 'nas_ip_addr': nas_ip_addr,
            "nas_port": nas_port,
            "customer_device_mac": customer_mac,
        }
    )
    ser.is_valid(raise_exception=True)
    save_radius_acct(event_time=event_time, data=ser.data)


@receiver(custom_signals.radius_auth_stop_signal, sender=CustomerRadiusSession)
def signal_radius_session_acct_stop(
    sender, instance_queryset, data: dict, ip_addr: str, radius_unique_id: str, customer_mac: str, *args, **kwargs
):

    with open("/tmp/radius_stop.log", "a") as f:
        dump(data, f)
        f.write('MAC: ERX-Dhcp-Mac-Addr "%s"\n' % customer_mac)
        f.write("\n"*3)

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

    ser = AAAExportSerializer(
        data={
            "event_time": event_time,
            "event_type": AAAEventType.RADIUS_AUTH_STOP,
            "session_id": radius_unique_id,
            "customer_ip": ip_addr,
            "customer_db_username": customer_username,
            # 'nas_ip_addr': nas_ip_addr,
            "nas_port": nas_port,
            "customer_device_mac": customer_mac,
        }
    )
    ser.is_valid(raise_exception=True)
    save_radius_acct(event_time=event_time, data=ser.data)
