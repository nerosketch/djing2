# from django.contrib.auth.models import User
from rest_framework.serializers import ModelSerializer
from rest_framework.exceptions import ValidationError

from profiles.models import UserProfile, UserProfileLog


class UserProfileSerializer(ModelSerializer):
    firbidden_usernames = ('log', 'api-token-auth')

    class Meta:
        model = UserProfile
        fields = ('pk', 'username', 'fio', 'is_active', 'is_admin', 'telephone',
                  'avatar', 'email')

    def create(self, validated_data):
        return UserProfile.objects.create_superuser(
            telephone=validated_data.get('telephone'),
            username=validated_data.get('username'),
            password=validated_data.get('password')
        )
        # return UserProfile.objects.create(**validated_data)

    def validate(self, attrs):
        print('Attrs:', attrs)
        return super().validate(attrs)

    def is_valid(self, raise_exception: bool = ...):
        if self.initial_data['username'] in self.firbidden_usernames:
            if raise_exception:
                raise ValidationError({'username': ['Forbidden username']})
            return True
        return super().is_valid(raise_exception)


class UserProfileLogSerializer(ModelSerializer):
    class Meta:
        model = UserProfileLog
        fields = ('do_type', 'additional_text', 'action_date')
