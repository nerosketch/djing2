from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from djing2.lib.mixins import BaseCustomModelSerializer
from profiles.models import UserProfile, UserProfileLog


class UserProfileSerializer(BaseCustomModelSerializer):
    forbidden_usernames = ('log', 'api-token-auth', 'api')
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = UserProfile
        fields = ('pk', 'username', 'fio', 'is_active', 'is_admin', 'telephone',
                  'avatar', 'email', 'full_name', 'last_login', 'is_superuser')

    def create(self, validated_data):
        return UserProfile.objects.create_superuser(
            telephone=validated_data.get('telephone'),
            username=validated_data.get('username'),
            password=validated_data.get('password')
        )
        # return UserProfile.objects.create(**validated_data)

    def is_valid(self, raise_exception: bool = ...):
        if self.initial_data['username'] in self.forbidden_usernames:
            if raise_exception:
                raise ValidationError({'username': ['Forbidden username']})
            return True
        return super().is_valid(raise_exception)


class UserProfileLogSerializer(BaseCustomModelSerializer):
    do_type_text = serializers.CharField(source='get_do_type_display', read_only=True)

    class Meta:
        model = UserProfileLog
        fields = ('do_type', 'additional_text', 'action_date',
                  'do_type_text')
