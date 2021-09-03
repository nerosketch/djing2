from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserProfile
from rest_framework.authtoken.models import Token


@receiver(post_save, sender=UserProfile)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created and instance:
        Token.objects.create(user=instance)
