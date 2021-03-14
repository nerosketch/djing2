from typing import List

from django.dispatch import receiver


try:
    from devices.custom_signals import device_monitoring_event_signal
    from devices.models import Device
    from messenger.tasks import multicast_viber_notify

    @receiver(device_monitoring_event_signal, sender=Device,
              dispatch_uid='dev_monitoring_viber_ev_unique6%487*@')
    def on_device_monitoring_event(sender, instance: Device, recipients: List[int], text: str, **kwargs):
        multicast_viber_notify(
            messenger_id=None,
            account_id_list=recipients,
            message_text=text
        )

except ImportError:
    pass
