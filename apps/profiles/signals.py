import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserProfile
from profiles.tasks import resize_profile_avatar
from rest_framework.authtoken.models import Token


@receiver(post_save, sender=UserProfile)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created and instance:
        Token.objects.create(user=instance)

    # run resize avatar task
    # TODO: not resize when it not changed
    if instance.avatar and os.path.isfile(instance.avatar.path):
        resize_profile_avatar.delay(instance.avatar.path)
