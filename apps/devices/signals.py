from django.db.models.signals import post_delete
from django.dispatch.dispatcher import receiver

from .models import Device
from .tasks import unregister_device_async


@receiver(post_delete, sender=Device)
def post_delete_device(sender, instance, **kwargs):
    unregister_device_async(instance.pk)
