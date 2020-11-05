from ipaddress import ip_address, ip_network

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.decorators import method_decorator
from django.views.generic.base import View
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer
from rest_framework.views import APIView
from drf_queryfields import QueryFieldsMixin

from .decorators import hash_auth_view


@method_decorator(hash_auth_view, name='dispatch')
class HashAuthView(APIView):

    def __init__(self, *args, **kwargs):
        api_auth_secret = getattr(settings, 'API_AUTH_SECRET')
        if api_auth_secret is None or api_auth_secret == 'your api secret':
            raise ImproperlyConfigured('You must specified API_AUTH_SECRET in settings')
        else:
            super().__init__(*args, **kwargs)


class AuthenticatedOrHashAuthView(HashAuthView):

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.is_admin:
                return View.dispatch(self, request, *args, **kwargs)
            else:
                return Response(status=status.HTTP_403_FORBIDDEN)
        else:
            return HashAuthView.dispatch(self, request, *args, **kwargs)


class AllowedSubnetMixin(object):
    def dispatch(self, request, *args, **kwargs):
        """
        Check if user ip in allowed subnet.
        Return 403 denied otherwise.
        """
        ip = ip_address(request.META.get('REMOTE_ADDR'))
        api_auth_subnet = getattr(settings, 'API_AUTH_SUBNET')
        if isinstance(api_auth_subnet, str):
            if ip in ip_network(api_auth_subnet):
                return super().dispatch(request, *args, **kwargs)
        try:
            for subnet in api_auth_subnet:
                if ip in ip_network(subnet, strict=False):
                    return super().dispatch(request, *args, **kwargs)
        except TypeError:
            if ip in ip_network(str(api_auth_subnet)):
                return super().dispatch(request, *args, **kwargs)
        return Response(status=status.HTTP_403_FORBIDDEN)


class SecureApiView(AllowedSubnetMixin, HashAuthView):
    permission_classes = [AllowAny]


class BaseCustomModelSerializer(QueryFieldsMixin, ModelSerializer):
    pass
