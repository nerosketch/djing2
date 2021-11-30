from django.dispatch import receiver
from django.db.models.signals import (
    post_save, post_delete,
    pre_save, pre_delete
)
from django.contrib.contenttypes.models import ContentType

from webhooks.models import HookObserverNotificationTypes
from webhooks.tasks import send_update2observers


def _send2task(notify_type: HookObserverNotificationTypes, instance_pk, sender):
    content_type = ContentType.objects.get_for_model(sender)
    app_label_str = str(content_type.app_label)
    model_str = str(content_type.model)
    send_update2observers(
        notification_type=notify_type.value,
        instance_id=instance_pk,
        app_label=app_label_str,
        model=model_str
    )


@receiver(post_save)
def _post_save_signal_handler(sender, instance, created=False, **kwargs):
    _send2task(
        notify_type=HookObserverNotificationTypes.MODEL_POST_SAVE,
        instance_pk=instance.pk,
        sender=sender
    )


@receiver(post_delete)
def _post_del_signal_handler(sender, instance, **kwargs):
    _send2task(
        notify_type=HookObserverNotificationTypes.MODEL_POST_DELETE,
        instance_pk=instance.pk,
        sender=sender
    )


# @receiver(post_init)
# def _post_init_signal_handler(sender, **kwargs):
#     print('_post_init_signal_handler', sender, kwargs)


@receiver(pre_save)
def _pre_save_signal_handler(sender, instance, **kwargs):
    _send2task(
        notify_type=HookObserverNotificationTypes.MODEL_PRE_SAVE,
        instance_pk=instance.pk if instance else None,
        sender=sender
    )


@receiver(pre_delete)
def _pre_del_signal_handler(sender, instance, **kwargs):
    _send2task(
        notify_type=HookObserverNotificationTypes.MODEL_PRE_DELETE,
        instance_pk=instance.pk,
        sender=sender
    )


# @receiver(pre_init)
# def _pre_init_signal_handler(sender, **kwargs):
#     print('_pre_init_signal_handler', sender, kwargs)
