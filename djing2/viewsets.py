from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from guardian.core import ObjectPermissionChecker
from guardian.ctypes import get_content_type
from guardian.shortcuts import assign_perm, get_perms, get_groups_with_perms
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet, GenericViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import AuthenticationFailed

from djing2.lib import safe_int
from djing2.permissions import IsSuperUser
from djing2.serializers import RequestObjectsPermsSerializer
from profiles.models import BaseAccount
from djing2.exceptions import UniqueConstraintIntegrityError


class DjingModelViewSet(ModelViewSet):

    def perform_create(self, serializer) -> None:
        try:
            super().perform_create(serializer)
        except IntegrityError as e:
            raise UniqueConstraintIntegrityError(str(e))

    def perform_update(self, serializer) -> None:
        try:
            super().perform_update(serializer)
        except IntegrityError as e:
            raise UniqueConstraintIntegrityError(str(e))

    def perform_destroy(self, instance) -> None:
        try:
            super().perform_destroy(instance)
        except IntegrityError as e:
            raise UniqueConstraintIntegrityError(str(e))

    @action(detail=False)
    def get_initial(self, request):
        serializer = self.get_serializer()
        return Response(serializer.get_initial())

    # Cache requested url for each user for 4 hours
    # @method_decorator(cache_page(60 * 60 * 4))
    # @method_decorator(vary_on_cookie)
    # def list(self, request, *args, **kwargs):
    #     return super().list(request, *args, **kwargs)

    def check_permission_code(self, request, perm_codename: str):
        if not request.user.has_perm(perm=perm_codename):
            self.permission_denied(request)

    @action(detail=True, methods=['put'])
    def set_object_perms(self, request, *args, **kwargs):
        # request.data = {
        #     'groupIds': [1, 2, 3],
        #     'selectedPerms': [1, 2, 3]
        # }
        serializer = RequestObjectsPermsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        group_ids = [safe_int(i) for i in data.get('groupIds') if safe_int(i) > 0]
        if len(group_ids) == 0:
            return Response('bad groupIds', status=status.HTTP_400_BAD_REQUEST)

        selected_perms = [safe_int(i) for i in data.get('selectedPerms') if safe_int(i) > 0]
        if len(selected_perms) == 0:
            return Response('bad selectedPerms', status=status.HTTP_400_BAD_REQUEST)

        selected_groups = Group.objects.filter(pk__in=group_ids)
        selected_perms = Permission.objects.filter(pk__in=selected_perms)
        obj = self.get_object()

        for perm in selected_perms.iterator():
            assign_perm(perm, selected_groups, obj)
        return Response()

    @action(detail=True)
    def get_object_perms(self, *args, **kwargs):
        obj = self.get_object()
        groups = get_groups_with_perms(obj)

        ctype = get_content_type(obj)
        perms_qs = Permission.objects.filter(content_type=ctype)

        return {
            'groupIds': groups.values_list('pk', flat=True),
            'selectedPerms': perms_qs.values_list('pk', flat=True)
        }


class DjingSuperUserModelViewSet(DjingModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser, IsSuperUser]


class DjingListAPIView(ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]


class BaseNonAdminReadOnlyModelViewSet(ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        if isinstance(self.request.user, BaseAccount):
            return super().get_queryset()
        raise AuthenticationFailed


class BaseNonAdminModelViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        if isinstance(self.request.user, BaseAccount):
            return super().get_queryset()
        raise AuthenticationFailed


class DjingAuthorizedViewSet(GenericViewSet):
    permission_classes = (IsAuthenticated, IsAdminUser)
