from typing import List

from django.dispatch import receiver

from djing2.lib.custom_signals import notification_signal

from messenger.tasks import multicast_viber_notify


@receiver(notification_signal, dispatch_uid="dev_monitoring_viber_ev_unique6%487*@")
def on_device_monitoring_event(sender, instance, recipients: List[int], text: str, **kwargs):
    multicast_viber_notify(messenger_id=None, account_id_list=recipients, message_text=text)
