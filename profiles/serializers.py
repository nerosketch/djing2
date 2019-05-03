# from django.contrib.auth.models import User
from rest_framework import serializers

from profiles.models import UserProfile, UserProfileLog


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('username', 'fio', 'is_active', 'is_admin', 'telephone',
                  'avatar', 'email', 'password')

    def create(self, validated_data):
        print(validated_data)
        UserProfile.objects.create_superuser()
        return UserProfile.objects.create(**validated_data)



class UserProfileLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfileLog
        fields = ('do_type', 'additional_text', 'action_date')
