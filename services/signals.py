from django.dispatch import receiver
from django.db import IntegrityError
from django.db.models.signals import pre_delete
from .models import PeriodicPay


@receiver(pre_delete, sender=PeriodicPay)
def periodic_pay_pre_delete(sender, **kwargs):
    raise IntegrityError('All linked abonapp.PeriodicPayForId will be removed, be careful')
