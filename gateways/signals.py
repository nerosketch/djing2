from django.utils.translation import gettext_lazy as _
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.contrib.messages import MessageFailure
from .models import Gateway


@receiver(pre_delete, sender=Gateway)
def nas_pre_delete(sender, **kwargs):
    nas = kwargs.get("instance")
    # check if this gateway is default.
    # You cannot remove default server
    if nas.is_default:
        raise MessageFailure(_('You cannot remove default server'))
