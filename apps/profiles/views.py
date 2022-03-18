from django.contrib.auth import authenticate
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.utils.translation import gettext, gettext_lazy as _
from guardian.models import GroupObjectPermission, UserObjectPermission
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.authtoken.models import Token

from djing2.lib.mixins import SitesFilterMixin
from djing2.viewsets import DjingModelViewSet, BaseNonAdminReadOnlyModelViewSet, DjingSuperUserModelViewSet
from profiles.models import UserProfile, UserProfileLog, ProfileAuthLog
from profiles.serializers import (
    UserProfileSerializer,
    UserProfileLogSerializer,
    UserProfilePasswordSerializer,
    UserObjectPermissionSerializer,
    GroupObjectPermissionSerializer,
    PermissionModelSerializer,
    ContentTypeModelSerializer,
    UserGroupModelSerializer,
    SitesAuthTokenSerializer,
    ProfileAuthLogSerializer,
)


class UserProfileViewSet(SitesFilterMixin, DjingModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = "username"

    def filter_queryset(self, queryset):
        if self.request.user.is_superuser:
            return super().get_queryset()
        filter_kwargs = {
            'sites': self.request.site
        }
        return queryset.filter(**filter_kwargs)

    @action(detail=False, methods=["get"], url_path=r"get_profiles_by_group/(?P<group_id>\d{1,9})")
    def get_profiles_by_group(self, request, group_id: str):
        profile_ids = UserProfile.objects.get_profiles_by_group(group_id).values_list("pk", flat=True)
        return Response(data=profile_ids)

    @action(detail=True, methods=["get"])
    def get_responsibility_groups(self, request, username=None):
        profile = self.get_object()
        group_ids = profile.responsibility_groups.values_list("pk", flat=True)
        return Response(data=group_ids)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsAdminUser])
    def get_active_profiles(self, request):
        queryset = self.filter_queryset(self.get_queryset()).filter(is_active=True)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=("put",))
    def set_responsibility_groups(self, request, username=None):
        profile = self.get_object()

        checked_groups = (int(gi) for gi in request.data.get("groups"))
        # profile.responsibility_groups.clear()
        profile.responsibility_groups.set(checked_groups)
        return Response()

    @staticmethod
    def _check_passw_data(data):
        serializer = UserProfilePasswordSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.data

    @action(detail=True, methods=("put",))
    def change_password(self, request, username=None):
        data = self._check_passw_data(request.data)

        old_passw = data.get("old_passw")
        new_passw = data.get("new_passw")

        profile = self.get_object()

        if not request.user.is_superuser:
            if request.user.pk != profile.pk:
                return Response(status=status.HTTP_403_FORBIDDEN)
            if old_passw != new_passw:
                return Response(_("Passwords must be same"), status=status.HTTP_400_BAD_REQUEST)
            if not profile.check_password(old_passw):
                return Response(_("Wrong old password"), status=status.HTTP_400_BAD_REQUEST)
        # validate_password(old_passw, profile)

        profile.set_password(new_passw)
        profile.save(update_fields=["password"])
        return Response("ok", status=status.HTTP_200_OK)

    @change_password.mapping.get
    def change_password_get(self, request, **kwargs):
        ser = UserProfilePasswordSerializer()
        return Response(ser.data)

    @action(detail=False, methods=('get',), permission_classes=[IsAuthenticated, IsAdminUser])
    def get_current_auth_permissions(self, request):
        return Response(list(request.user.get_all_permissions()))

    def perform_create(self, serializer, *args, **kwargs):
        return super().perform_create(serializer=serializer, sites=[self.request.site])


class UserProfileLogViewSet(DjingModelViewSet):
    queryset = UserProfileLog.objects.all()
    serializer_class = UserProfileLogSerializer
    filterset_fields = ("account",)

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(account=self.request.user)


class LocationAuth(APIView):
    throttle_classes = ()
    permission_classes = ()
    schema = AutoSchema()
    __doc__ = gettext("Login profile via customer's ip address")

    @staticmethod
    def get(request, *args, **kwargs):
        user = authenticate(request=request, byip=True)

        if not user:
            msg = _("Unable to log in with provided credentials")
            raise ValidationError(msg, code="authorization")

        if not user.sites.filter(pk=request.site.pk).exists():
            msg = _("Incorrect provided credentials.")
            raise ValidationError(msg, code="authorization")

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key})


class CurrentAuthenticatedProfileROViewSet(BaseNonAdminReadOnlyModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return UserProfile.objects.get(pk=self.request.user.pk)

    def list(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(pk=self.request.user.pk)


class UserObjectPermissionViewSet(DjingSuperUserModelViewSet):
    queryset = UserObjectPermission.objects.all()
    serializer_class = UserObjectPermissionSerializer


class GroupObjectPermissionViewSet(DjingSuperUserModelViewSet):
    queryset = GroupObjectPermission.objects.all()
    serializer_class = GroupObjectPermissionSerializer


class PermissionViewSet(DjingSuperUserModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionModelSerializer


class ContentTypeViewSet(DjingSuperUserModelViewSet):
    queryset = ContentType.objects.all()
    serializer_class = ContentTypeModelSerializer


class UserGroupModelViewSet(DjingSuperUserModelViewSet):
    queryset = Group.objects.annotate(permcount=Count("permissions"), usercount=Count("user"))
    serializer_class = UserGroupModelSerializer


class SitesObtainAuthToken(ObtainAuthToken):
    serializer_class = SitesAuthTokenSerializer


class ProfileAuthLogViewSet(ReadOnlyModelViewSet):
    queryset = ProfileAuthLog.objects.all()
    serializer_class = ProfileAuthLogSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("profile",)

    def filter_queryset(self, queryset):
        if self.request.user.is_superuser:
            return super().filter_queryset(queryset)
        return queryset.filter(profile=self.request.user)
