from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from djing2.lib.mixins import BaseCustomModelSerializer
from profiles.models import UserProfile, UserProfileLog


class UserProfileSerializer(BaseCustomModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    password = serializers.CharField(write_only=True)
    create_date = serializers.CharField(read_only=True)

    class Meta:
        model = UserProfile
        fields = ('pk', 'username', 'fio', 'birth_day', 'create_date', 'is_active',
                  'is_admin', 'telephone', 'avatar', 'email', 'full_name',
                  'last_login', 'is_superuser', 'password')

    def create(self, validated_data):
        return UserProfile.objects.create_superuser(
            telephone=validated_data.get('telephone'),
            username=validated_data.get('username'),
            password=validated_data.get('password'),
            fio=validated_data.get('fio'),
            email=validated_data.get('email'),
            is_active=validated_data.get('is_active'),
            birth_day=validated_data.get('birth_day'),
        )
        # return UserProfile.objects.create(**validated_data)

    def is_valid(self, raise_exception: bool = ...):
        forbidden_usernames = ('log', 'api-token-auth', 'api')
        if hasattr(self.initial_data, 'username') and self.initial_data['username'] in forbidden_usernames:
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
