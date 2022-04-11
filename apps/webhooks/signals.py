import sys
from typing import Optional, Any
from django.dispatch import receiver
from django.db.models.signals import (
    post_save, post_delete,
    pre_save, pre_delete
)
from rest_framework.serializers import ModelSerializer
from webhooks.models import HookObserverNotificationTypes
from webhooks.tasks import send_update2observers_task


def _model_instance_to_dict(instance, model_class) -> dict:
    class _model_serializer(ModelSerializer):
        class Meta:
            model = model_class
            fields = '__all__'
    ser = _model_serializer(instance=instance)
    return ser.data


def receiver_no_test(*args, **kwargs):
    def _wrapper(fn):
        if 'test' in sys.argv:
            return fn
        return receiver(*args, **kwargs)(fn)

    return _wrapper


def _send2task(notify_type: HookObserverNotificationTypes, instance: Optional[Any], sender):
    app_label_str = sender._meta.app_label
    model_str = sender._meta.object_name

    if instance:
        instance_data = _model_instance_to_dict(
            instance=instance,
            model_class=sender
        )
    else:
        instance_data = None

    send_update2observers_task(
        notification_type=notify_type.value,
        app_label=app_label_str,
        model_str=model_str,
        data=instance_data,
    )


@receiver_no_test(post_save)
def _post_save_signal_handler(sender, instance, **kwargs):
    _send2task(
        notify_type=HookObserverNotificationTypes.MODEL_POST_SAVE,
        instance=instance,
        sender=sender
    )


@receiver_no_test(post_delete)
def _post_del_signal_handler(sender, instance, **kwargs):
    _send2task(
        notify_type=HookObserverNotificationTypes.MODEL_POST_DELETE,
        instance=instance,
        sender=sender
    )


# @receiver(post_init)
# def _post_init_signal_handler(sender, **kwargs):
#     print('_post_init_signal_handler', sender, kwargs)


@receiver_no_test(pre_save)
def _pre_save_signal_handler(sender, instance, **kwargs):
    _send2task(
        notify_type=HookObserverNotificationTypes.MODEL_PRE_SAVE,
        instance=instance if instance else None,
        sender=sender
    )


@receiver_no_test(pre_delete)
def _pre_del_signal_handler(sender, instance, **kwargs):
    _send2task(
        notify_type=HookObserverNotificationTypes.MODEL_PRE_DELETE,
        instance=instance,
        sender=sender
    )


# @receiver(pre_init)
# def _pre_init_signal_handler(sender, **kwargs):
#     print('_pre_init_signal_handler', sender, kwargs)
