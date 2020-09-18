from django.contrib.auth.models import Permission, Group as ProfileGroup
from django.db import IntegrityError
from guardian.ctypes import get_content_type
from guardian.shortcuts import assign_perm, get_groups_with_perms, remove_perm
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView, get_object_or_404
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
        if not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = RequestObjectsPermsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        group_ids = [safe_int(i) for i in data.get('groupIds') if safe_int(i) > 0]

        selected_perms = [safe_int(i) for i in data.get('selectedPerms') if safe_int(i) > 0]

        selected_groups = ProfileGroup.objects.filter(pk__in=group_ids)
        selected_perms = Permission.objects.filter(pk__in=selected_perms).iterator()

        obj = self.get_object()
        ctype = get_content_type(obj)
        existing_perm_codes = {p.codename for p in Permission.objects.filter(
            groupobjectpermission__content_type=ctype,
            groupobjectpermission__object_pk__in=[obj.pk]
        ).iterator()}

        selected_perm_codes = {p.codename for p in selected_perms}
        for_del = existing_perm_codes - selected_perm_codes
        for_add = selected_perm_codes - existing_perm_codes

        # del perms
        for perm in for_del:
            for grp in selected_groups:
                remove_perm(perm, grp, obj)

        # add perms
        for perm in for_add:
            assign_perm(perm, selected_groups, obj)
        return Response('ok')

    @action(detail=True)
    def get_object_perms(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        obj = self.get_object()

        available_perms = Permission.objects.filter(
            content_type=get_content_type(obj)
        )

        available_perms = available_perms.values('id', 'name', 'content_type', 'codename')

        groups = get_groups_with_perms(obj).values_list('pk', flat=True)
        return Response({
            'groupIds': groups,
            'availablePerms': available_perms
        })

    @action(detail=True, url_path="get_selected_object_perms/(?P<profile_group_id>\d+)")
    def get_selected_object_perms(self, request, profile_group_id, pk=None):
        if not request.user.is_superuser:
            return Response(status=status.HTTP_403_FORBIDDEN)

        obj = self.get_object()

        selected_perms = Permission.objects.filter(
            content_type=get_content_type(obj),
            groupobjectpermission__object_pk__in=[pk],
            groupobjectpermission__group=profile_group_id
        ).values_list('id', flat=True)
        return Response(selected_perms)


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
