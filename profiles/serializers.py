# from django.contrib.auth.models import User
from rest_framework import serializers

from profiles.models import UserProfile, UserProfileLog


class UserProfileSerializer(serializers.ModelSerializer):
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


class UserProfileLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfileLog
        fields = ('do_type', 'additional_text', 'action_date')
