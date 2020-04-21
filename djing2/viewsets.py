from django.db import IntegrityError
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet, GenericViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser, DjangoObjectPermissions
from rest_framework.exceptions import AuthenticationFailed


from profiles.models import BaseAccount
from djing2.exceptions import UniqueConstraintIntegrityError


class GuardianObjectPermissions(DjangoObjectPermissions):
    """
    Similar to `DjangoObjectPermissions`, but adding 'view' permissions.
    """
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': ['%(app_label)s.view_%(model_name)s'],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }


_admin_permission_classes = (IsAuthenticated, IsAdminUser, GuardianObjectPermissions)


class DjingModelViewSet(ModelViewSet):
    permission_classes = _admin_permission_classes

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

    @action(methods=('get',), detail=False)
    def get_initial(self, request):
        serializer = self.get_serializer()
        return Response(serializer.get_initial())

    # Cache requested url for each user for 4 hours
    # @method_decorator(cache_page(60 * 60 * 4))
    # @method_decorator(vary_on_cookie)
    # def list(self, request, *args, **kwargs):
    #     return super().list(request, *args, **kwargs)


class DjingListAPIView(ListAPIView):
    permission_classes = _admin_permission_classes


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
    permission_classes = _admin_permission_classes
