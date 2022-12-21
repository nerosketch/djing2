from typing import Optional, Union, Type
from django.db.models import QuerySet, Model
from django.contrib.sites.models import Site
from djing2.lib.fastapi.perms import permission_check_dependency
from fastapi import Depends
from profiles.models import BaseAccount
from .perms import filter_qs_by_rights
from .sites_depend import filter_qs_with_sites, sites_dependency


def general_filter_queryset(qs_or_model: Union[QuerySet, Type[Model]], curr_user: BaseAccount,
                            perm_codename: Union[str, list[str]], curr_site: Optional[Site]
                            ) -> QuerySet:
    rqs = filter_qs_by_rights(
        qs_or_model=qs_or_model,
        curr_user=curr_user,
        perm_codename=perm_codename
    )
    rqs = filter_qs_with_sites(
        qs=rqs,
        curr_user=curr_user,
        curr_site=curr_site
    )
    return rqs


# TODO: Use it instead of general_filter_queryset in many routes
def general_prepare_queryset_dependency(perm_codename, qs_or_model: Union[QuerySet, Type[Model]]):
    def _w(
        curr_site: Site = Depends(sites_dependency),
        curr_user: BaseAccount = Depends(permission_check_dependency(
            perm_codename=perm_codename
        )),
    ) -> QuerySet:
        qs = general_filter_queryset(
            qs_or_model=qs_or_model,
            curr_site=curr_site,
            curr_user=curr_user,
            perm_codename=perm_codename
        )
        return qs

    return _w
