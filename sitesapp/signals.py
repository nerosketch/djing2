from django.contrib.sites.models import Site
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from rest_framework.exceptions import MethodNotAllowed


@receiver(pre_delete, sender=Site)
def site_pre_delete(sender, **kwargs):
    raise MethodNotAllowed(
        method='delete',
        detail='Removing sites is temporary forbidden'
    )
