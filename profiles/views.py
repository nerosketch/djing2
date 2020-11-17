from django.contrib.auth import authenticate
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from guardian.models import GroupObjectPermission, UserObjectPermission
from rest_framework import status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from djing2.lib.mixins import SitesFilterMixin
from djing2.viewsets import (
    DjingModelViewSet, BaseNonAdminReadOnlyModelViewSet,
    DjingSuperUserModelViewSet
)
from profiles.models import UserProfile, UserProfileLog
from profiles.serializers import (
    UserProfileSerializer, UserProfileLogSerializer,
    UserProfilePasswordSerializer,
    UserObjectPermissionSerializer,
    GroupObjectPermissionSerializer,
    PermissionModelSerializer,
    ContentTypeModelSerializer,
    UserGroupModelSerializer, SitesAuthTokenSerializer)


class UserProfileViewSet(SitesFilterMixin, DjingSuperUserModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    lookup_field = 'username'

    @action(detail=False, url_path='get_profiles_by_group/(?P<group_id>\d{1,9})')
    def get_profiles_by_group(self, request, group_id: str):
        profile_ids = UserProfile.objects.get_profiles_by_group(group_id).values_list('pk', flat=True)
        return Response(data=profile_ids)

    @action(detail=True)
    def get_responsibility_groups(self, request, username=None):
        profile = self.get_object()
        group_ids = profile.responsibility_groups.values_list('pk', flat=True)
        return Response(data=group_ids)

    @action(detail=False, permission_classes=[IsAuthenticated, IsAdminUser])
    def get_active_profiles(self, request):
        queryset = self.filter_queryset(
            self.get_queryset().filter(
                is_active=True
            )
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=('put',))
    def set_responsibility_groups(self, request, username=None):
        profile = self.get_object()

        checked_groups = (int(gi) for gi in request.data.get('groups'))
        # profile.responsibility_groups.clear()
        profile.responsibility_groups.set(checked_groups)
        return Response()

    @staticmethod
    def _check_passw_data(data):
        serializer = UserProfilePasswordSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.data

    @action(detail=True, methods=('put', 'get'))
    def change_password(self, request, username=None):
        if request.method == 'GET':
            ser = UserProfilePasswordSerializer()
            return Response(ser.data)
        data = self._check_passw_data(request.data)

        old_passw = data.get('old_passw')
        new_passw = data.get('new_passw')

        profile = self.get_object()

        if not request.user.is_superuser:
            if old_passw != new_passw:
                return Response(_('Passwords must be same'), status=status.HTTP_400_BAD_REQUEST)
            if not profile.check_password(old_passw):
                return Response(_('Wrong old password'), status=status.HTTP_400_BAD_REQUEST)

        profile.set_password(new_passw)
        profile.save(update_fields=['password'])
        return Response('ok', status=status.HTTP_200_OK)

    @action(detail=False, permission_classes=[IsAuthenticated, IsAdminUser])
    def get_current_auth_permissions(self, request):
        return Response(request.user.get_all_permissions())

    def perform_create(self, serializer, *args, **kwargs):
        return super().perform_create(
            serializer=serializer,
            sites=[self.request.site]
        )


class UserProfileLogViewSet(DjingModelViewSet):
    queryset = UserProfileLog.objects.all()
    serializer_class = UserProfileLogSerializer
    filterset_fields = ('account',)


class LocationAuth(APIView):
    throttle_classes = ()
    permission_classes = ()

    @staticmethod
    def get(request, *args, **kwargs):
        user = authenticate(
            request=request,
            byip=True
        )

        if not user:
            msg = _('Unable to log in with provided credentials.')
            raise ValidationError(msg, code='authorization')

        if not user.sites.filter(pk=request.site.pk).exists():
            msg = _('Incorrect provided credentials.')
            raise ValidationError(msg, code='authorization')

        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})


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
    queryset = Group.objects.annotate(
        permcount=Count('permissions'),
        usercount=Count('user')
    )
    serializer_class = UserGroupModelSerializer


class SitesObtainAuthToken(ObtainAuthToken):
    serializer_class = SitesAuthTokenSerializer
