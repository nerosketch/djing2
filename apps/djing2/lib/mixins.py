from django.conf import settings
from django.contrib.sites.middleware import CurrentSiteMiddleware
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.http import JsonResponse
from django.db.models import Q
from guardian.shortcuts import get_objects_for_user
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.serializers import ModelSerializer
from drf_queryfields import QueryFieldsMixin
from djing2.lib import check_sign, check_subnet
from pydantic import BaseModel, validator

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
        try:
            check_subnet(request.META)
            return super().dispatch(request, *args, **kwargs)
        except ValueError as err:
            return JsonResponseForbidden(str(err))


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


class RemoveFilterQuerySetMixin:
    def remove_filter(self, lookup):
        """Remove filter lookup in queryset"""
        query = self.query
        q = Q(**{lookup: None})
        clause, _ = query._add_q(q, query.used_aliases)

        def _filter_lookups(child):
            return child.lhs.target != clause.children[0].lhs.target

        query.where.children = list(filter(_filter_lookups, query.where.children))
        return self


class SitesBaseSchema(BaseModel):
    sites: list[int] = []

    @validator('sites', pre=True)
    def format_sites(cls, sites):
        if isinstance(sites, (list, tuple)):
            return [s.pk if isinstance(s, Site) else int(s) for s in sites]
        try:
            return [int(s) for s in sites]
        except TypeError:
            pass
        return [int(s.pk) for s in sites.all()]
