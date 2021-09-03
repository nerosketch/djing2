from django.utils.translation import gettext_lazy as _
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver
from django.contrib.messages import MessageFailure
from .models import Gateway


@receiver(pre_delete, sender=Gateway)
def gw_pre_delete(sender, **kwargs):
    gw = kwargs.get("instance")
    # check if this gateway is default.
    # You cannot remove default server
    if gw.is_default:
        raise MessageFailure(_("You cannot remove default server"))


@receiver(pre_save, sender=Gateway)
def gw_pre_save(sender, **kwargs):
    gw = kwargs.get("instance")
    if gw.is_default:
        if Gateway.objects.filter(is_default=True).exists():
            raise MessageFailure(_("You can't have two default gateways"))
