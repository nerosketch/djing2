from django.contrib.auth import authenticate
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from guardian.models import GroupObjectPermission, UserObjectPermission
from django.utils.translation import gettext_lazy as _
from profiles.schemas import generate_random_username, generate_random_password
from rest_framework import serializers
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.exceptions import ValidationError, PermissionDenied

from djing2.lib.mixins import BaseCustomModelSerializer
from profiles.models import BaseAccount, UserProfile, UserProfileLog, ProfileAuthLog


class BaseAccountSerializer(BaseCustomModelSerializer):
    is_active = serializers.BooleanField(initial=False, default=False)
    username = serializers.CharField(initial=generate_random_username)
    password = serializers.CharField(
        write_only=True, required=False, initial=generate_random_password
    )
    full_name = serializers.CharField(source="get_full_name", read_only=True)

    def update(self, instance, validated_data):
        if not self.context['request'].user.is_superuser:
            validated_data.pop('is_superuser', None)
            validated_data.pop('groups', None)
            validated_data.pop('user_permissions', None)
        return super().update(instance, validated_data)

    class Meta:
        model = BaseAccount


class UserProfileSerializer(BaseAccountSerializer):
    create_date = serializers.CharField(read_only=True)
    access_level = serializers.IntegerField(source="calc_access_level_percent", read_only=True)
    avatar = serializers.SerializerMethodField()

    def get_avatar(self, data):
        return data.get_avatar_url()

    class Meta:
        model = UserProfile
        fields = '__all__'

    def create(self, validated_data):
        return UserProfile.objects.create_superuser(
            telephone=validated_data.get("telephone"),
            username=validated_data.get("username"),
            password=validated_data.get("password"),
            fio=validated_data.get("fio"),
            email=validated_data.get("email"),
            is_active=validated_data.get("is_active"),
            birth_day=validated_data.get("birth_day"),
        )
        # return UserProfile.objects.create(**validated_data)

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if not request or not request.user:
            raise PermissionDenied
        if request.user.is_superuser or request.user.pk == instance.pk:
            return super().update(instance, validated_data)
        raise PermissionDenied

    def validate_password(self, value):
        try:
            validate_password(value)
            return value
        except DjangoValidationError as err:
            raise ValidationError(err) from err

    def is_valid(self, raise_exception: bool = ...):
        forbidden_usernames = ("log", "api-token-auth", "api")
        if hasattr(self.initial_data, "username") and self.initial_data["username"] in forbidden_usernames:
            if raise_exception:
                raise ValidationError({"username": ["Forbidden username"]})
            return True
        return super().is_valid(raise_exception)


class UserProfileLogSerializer(BaseCustomModelSerializer):
    do_type_text = serializers.CharField(source="get_do_type_display", read_only=True)

    class Meta:
        model = UserProfileLog
        fields = ("do_type", "additional_text", "action_date", "do_type_text")


class UserProfilePasswordSerializer(serializers.Serializer):
    old_passw = serializers.CharField(label="Old password", max_length=128, required=True)
    new_passw = serializers.CharField(label="Old password", max_length=128, required=True)

    def validate_new_passw(self, value):
        try:
            validate_password(value)
            return value
        except DjangoValidationError as err:
            raise ValidationError(err) from err


class UserObjectPermissionSerializer(BaseCustomModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=UserProfile.objects.all())

    class Meta:
        model = UserObjectPermission
        fields = "__all__"


class GroupObjectPermissionSerializer(BaseCustomModelSerializer):
    class Meta:
        model = GroupObjectPermission
        fields = "__all__"


class PermissionModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = Permission
        fields = "__all__"


class ContentTypeModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = ContentType
        fields = "__all__"


class UserGroupModelSerializer(BaseCustomModelSerializer):
    permcount = serializers.IntegerField(read_only=True)
    usercount = serializers.IntegerField(read_only=True)

    class Meta:
        model = Group
        fields = "__all__"


class SitesAuthTokenSerializer(AuthTokenSerializer):
    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            user = authenticate(request=self.context.get("request"), username=username, password=password)

            err_msg = _("Unable to log in with provided credentials")
            if not user:
                raise ValidationError(err_msg, code="authorization")

            if not user.is_superuser:
                if (
                    not self.context["request"].site
                    or not user.sites.filter(pk=self.context["request"].site.pk).exists()
                ):
                    raise ValidationError(err_msg, code="authorization")

        else:
            msg = _('Must include "username" and "password".')
            raise ValidationError(msg, code="authorization")

        attrs["user"] = user
        return attrs


class ProfileAuthLogSerializer(BaseCustomModelSerializer):
    class Meta:
        model = ProfileAuthLog
        fields = "__all__"
