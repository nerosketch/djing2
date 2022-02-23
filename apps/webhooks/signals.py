from typing import Optional, Any
from django.dispatch import receiver
from django.db.models.signals import (
    post_save, post_delete,
    pre_save, pre_delete
)
from django.contrib.contenttypes.models import ContentType
from rest_framework.serializers import ModelSerializer
from djing2.lib.logger import logger
from webhooks.models import HookObserverNotificationTypes
from webhooks.tasks import send_update2observers_task


def _model_instance_to_dict(instance, model_class) -> dict:
    class _model_serializer(ModelSerializer):
        class Meta:
            model = model_class
            fields = '__all__'
    ser = _model_serializer(instance=instance)
    return ser.data


def _send2task(notify_type: HookObserverNotificationTypes, instance: Optional[Any], sender):
    # TODO: Optimize it. It wll be execute every signal(many times)
    content_type = ContentType.objects.get_for_model(sender)
    app_label_str = str(content_type.app_label)
    model_str = str(content_type.model)

    model_class = content_type.model_class()
    if model_class is None:
        logger.error('send_update2observers() model_class is None')
        return

    if instance:
        instance_data = _model_instance_to_dict(instance, model_class)
    else:
        instance_data = None

    send_update2observers_task(
        notification_type=notify_type.value,
        app_label=app_label_str,
        model_str=model_str,
        data=instance_data,
    )


@receiver(post_save)
def _post_save_signal_handler(sender, instance, **kwargs):
    _send2task(
        notify_type=HookObserverNotificationTypes.MODEL_POST_SAVE,
        instance=instance,
        sender=sender
    )


@receiver(post_delete)
def _post_del_signal_handler(sender, instance, **kwargs):
    _send2task(
        notify_type=HookObserverNotificationTypes.MODEL_POST_DELETE,
        instance=instance,
        sender=sender
    )


# @receiver(post_init)
# def _post_init_signal_handler(sender, **kwargs):
#     print('_post_init_signal_handler', sender, kwargs)


@receiver(pre_save)
def _pre_save_signal_handler(sender, instance, **kwargs):
    _send2task(
        notify_type=HookObserverNotificationTypes.MODEL_PRE_SAVE,
        instance=instance if instance else None,
        sender=sender
    )


@receiver(pre_delete)
def _pre_del_signal_handler(sender, instance, **kwargs):
    _send2task(
        notify_type=HookObserverNotificationTypes.MODEL_PRE_DELETE,
        instance=instance,
        sender=sender
    )


# @receiver(pre_init)
# def _pre_init_signal_handler(sender, **kwargs):
#     print('_pre_init_signal_handler', sender, kwargs)
