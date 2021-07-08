from radiusapp import custom_signals
from django.dispatch.dispatcher import receiver
from networks.models import CustomerRadiusSession
from radiusapp.vendors import IVendorSpecific
from sorm_export.serializers.aaa import AAAExportSerializer, AAAEventType
from sorm_export.tasks.aaa import save_radius_acct_start


@receiver(custom_signals.radius_auth_start_signal, sender=CustomerRadiusSession)
def signal_radius_session_acc_start(
    sender,
    instance,
    data,
    ip_addr,
    radius_username,
    customer_ip_lease,
    customer,
    radius_unique_id,
    event_time,
    customer_mac: str,
):

    nas_port = (IVendorSpecific.get_rad_val(data, "NAS-Port", 0),)

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
    save_radius_acct_start(event_time=event_time, data=ser.data)
