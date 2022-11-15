from typing import Optional, Union, Type
from django.db.models import QuerySet, Model
from django.contrib.sites.models import Site
from profiles.models import BaseAccount
from .perms import filter_qs_by_rights
from .sites_depend import filter_qs_with_sites


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
