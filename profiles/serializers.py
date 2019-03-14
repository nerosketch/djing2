from rest_framework import serializers

from djing2.custom_mixins import VerboseModelSerializer
from profiles.models import UserProfile, UserProfileLog


class UserProfileSerializer(VerboseModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('username', 'fio', 'is_active', 'is_admin', 'telephone',
                  'avatar', 'email', 'responsibility_groups', 'flags', 'last_login',
                  'is_superuser', 'groups', 'user_permissions')


class UserProfileLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfileLog
        fields = ('do_type', 'additional_text', 'action_date')
