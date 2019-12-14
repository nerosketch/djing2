from django.db import IntegrityError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie
from rest_framework.generics import ListAPIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.exceptions import AuthenticationFailed


from profiles.models import BaseAccount
from djing2.exceptions import UniqueConstraintIntegrityError


class DjingModelViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def perform_create(self, serializer):
        try:
            return super().perform_create(serializer)
        except IntegrityError as e:
            raise UniqueConstraintIntegrityError(str(e))

    # Cache requested url for each user for 4 hours
    @method_decorator(cache_page(60 * 60 * 4))
    @method_decorator(vary_on_cookie)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class DjingListAPIView(ListAPIView):
    permission_classes = (IsAuthenticated, IsAdminUser)


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
