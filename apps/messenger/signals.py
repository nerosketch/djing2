from typing import List
from django.dispatch import receiver
from djing2.lib.custom_signals import notification_signal
from messenger.tasks import send_messenger_broadcast_message_task


@receiver(notification_signal, dispatch_uid="dev_monitoring_unique6%487*@")
def on_device_monitoring_event(sender, instance, recipients: List[int], text: str, **kwargs):
    """
    :param sender: May be different classes. For example Task or Device.
    :param instance: Instance of 'sender' class.
    :param recipients: List of UserProfile id.
    :param text: Message text.
    """
    # TODO: move to task server
    send_messenger_broadcast_message_task(
        text=text,
        recipients=recipients
    )
