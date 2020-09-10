from django.db import IntegrityError
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet, GenericViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import AuthenticationFailed

from djing2.permissions import CustomizedDjangoModelPermissions, IsSuperUser
from profiles.models import BaseAccount
from djing2.exceptions import UniqueConstraintIntegrityError


class DjingModelViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser, CustomizedDjangoModelPermissions]

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


class DjingSuperUserModelViewSet(DjingModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser, IsSuperUser]


class DjingListAPIView(ListAPIView):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def check_permission_code(self, request, perm_codename: str):
        if not request.user.has_perm(perm=perm_codename):
            self.permission_denied(request)


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
