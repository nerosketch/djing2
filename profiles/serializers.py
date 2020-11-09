from django.contrib.auth import authenticate
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from guardian.models import GroupObjectPermission, UserObjectPermission
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.exceptions import ValidationError

from djing2.lib.mixins import BaseCustomModelSerializer
from profiles.models import UserProfile, UserProfileLog


class UserProfileSerializer(BaseCustomModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    password = serializers.CharField(write_only=True)
    create_date = serializers.CharField(read_only=True)
    access_level = serializers.IntegerField(source='calc_access_level_percent', read_only=True)

    class Meta:
        model = UserProfile
        fields = ('pk', 'username', 'fio', 'birth_day', 'create_date', 'is_active',
                  'is_admin', 'telephone', 'avatar', 'email', 'full_name',
                  'last_login', 'is_superuser', 'password', 'groups', 'user_permissions',
                  'access_level', 'sites')

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


class UserProfilePasswordSerializer(serializers.Serializer):
    old_passw = serializers.CharField(label='Old password', max_length=128, required=True)
    new_passw = serializers.CharField(label='Old password', max_length=128, required=True)

    # def update(self, instance, validated_data):
    #     print('UserProfilePasswordSerializer.update', instance, validated_data)
    #     return instance

    # def create(self, validated_data):
    #     print('UserProfilePasswordSerializer.create', validated_data)


class UserObjectPermissionSerializer(BaseCustomModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=UserProfile.objects.all()
    )

    class Meta:
        model = UserObjectPermission
        fields = '__all__'


class GroupObjectPermissionSerializer(BaseCustomModelSerializer):
    class Meta:
        model = GroupObjectPermission
        fields = '__all__'


class PermissionModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = Permission
        fields = '__all__'


class ContentTypeModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = ContentType
        fields = '__all__'


class UserGroupModelSerializer(BaseCustomModelSerializer):
    permcount = serializers.IntegerField(read_only=True)
    usercount = serializers.IntegerField(read_only=True)

    class Meta:
        model = Group
        fields = '__all__'


class SitesAuthTokenSerializer(AuthTokenSerializer):

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)

            # The authenticate call simply returns None for is_active=False
            # users. (Assuming the default ModelBackend authentication
            # backend.)
            err_msg = _('Unable to log in with provided credentials.')
            if not user:
                raise serializers.ValidationError(err_msg, code='authorization')

            if not self.context['request'].site or not user.sites.filter(pk=self.context['request'].site.pk).exists():
                raise ValidationError(err_msg, code='authorization')

        else:
            msg = _('Must include "username" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs
