from ipaddress import ip_address, ip_network

from django.conf import settings
from django.contrib.sites.middleware import CurrentSiteMiddleware
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse
from guardian.shortcuts import get_objects_for_user
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.serializers import ModelSerializer
from drf_queryfields import QueryFieldsMixin
from djing2.lib import check_sign

from groupapp.models import Group


class JsonResponseForbidden(JsonResponse):
    status_code = status.HTTP_400_BAD_REQUEST

    def __init__(self, data, **kwargs):
        new_dat = {"error": data}
        super().__init__(data=new_dat, **kwargs)


class HashAuthViewMixin:
    def __init__(self, *args, **kwargs):
        api_auth_secret = getattr(settings, "API_AUTH_SECRET")
        if api_auth_secret is None or api_auth_secret == "your api secret":
            raise ImproperlyConfigured("You must specified API_AUTH_SECRET in settings")
        else:
            super().__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        sign = request.headers.get("Api-Auth-Sign")
        if not sign:
            sign = request.META.get("Api-Auth-Sign")
        if not sign:
            return JsonResponseForbidden("Access Denied!")
        get_values = request.GET.copy()
        if check_sign(get_values, sign):
            return super().dispatch(request, *args, **kwargs)
        else:
            return JsonResponseForbidden("Access Denied")


class AllowedSubnetMixin:
    def dispatch(self, request, *args, **kwargs):
        """
        Check if user ip in allowed subnet.
        Return 403 denied otherwise.
        """
        ip = ip_address(request.META.get("REMOTE_ADDR"))
        api_auth_subnet = getattr(settings, "API_AUTH_SUBNET")
        if isinstance(api_auth_subnet, str):
            if ip in ip_network(api_auth_subnet):
                return super().dispatch(request, *args, **kwargs)
        else:
            try:
                for subnet in api_auth_subnet:
                    if ip in ip_network(subnet, strict=False):
                        return super().dispatch(request, *args, **kwargs)
            except TypeError:
                if ip in ip_network(str(api_auth_subnet)):
                    return super().dispatch(request, *args, **kwargs)
        return JsonResponseForbidden("Bad Subnet")


class SecureApiViewMixin(AllowedSubnetMixin, HashAuthViewMixin):
    permission_classes = [AllowAny]


class BaseCustomModelSerializer(QueryFieldsMixin, ModelSerializer):
    pass


class GroupsFilterMixin:
    """
    Can use only if model has field groups
    groups = models.ManyToManyField(Group)
    """

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        # TODO: May optimize
        grps = get_objects_for_user(user=self.request.user, perms="groupapp.view_group", klass=Group).order_by("title")
        return qs.filter(groups__in=grps)


class SitesFilterMixin:
    """
    Can use only if model has field sites
    sites = models.ManyToManyField(Site)
    """

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_superuser:
            return qs
        return qs.filter(sites__in=[self.request.site])


class SitesGroupFilterMixin(SitesFilterMixin, GroupsFilterMixin):
    """
    Can use only if model has both fields groups and sites
    groups = models.ManyToManyField(Group)
    sites = models.ManyToManyField(Site)
    """


class CustomCurrentSiteMiddleware(CurrentSiteMiddleware):
    def process_request(self, request):
        try:
            return super().process_request(request=request)
        except Site.DoesNotExist:
            return JsonResponseForbidden("Bad Request (400). Unknown site.")
