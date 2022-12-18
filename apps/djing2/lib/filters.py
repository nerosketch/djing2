from operator import or_
from functools import reduce
from typing import Optional, Type, Any
from fastapi import Depends, Query
from django.db.models import Model, Q
from rest_framework_guardian.filters import ObjectPermissionsFilter
from rest_framework.filters import SearchFilter
from pydantic import create_model

from djing2.lib import safe_int


class CustomObjectPermissionsFilter(ObjectPermissionsFilter):
    shortcut_kwargs = {
        "accept_global_perms": True,
    }


class CustomSearchFilter(SearchFilter):
    def filter_queryset(self, request, queryset, view):
        # TODO: move 10 to settings
        qs = super().filter_queryset(request, queryset, view)
        search_str = request.query_params.get(self.search_param)
        if search_str is not None:
            search_len = request.query_params.get('search_len')
            if search_len:
                search_len = safe_int(search_len)
            else:
                search_len = 10
            qs = qs[:search_len]
        return qs


def filter_qs_by_fields_dependency(db_model: Type[Model], fields: dict[str, Any]):
    prms = {f_name: (Optional[f_type], None) for f_name, f_type in fields.items()}
    query_model = create_model(f'{db_model}FieldFilterSchema', **prms)
    del prms

    def _filter_dependency(params: query_model = Depends()) -> Q:
        dict_params = params.dict(exclude_none=True, exclude_unset=True, exclude_defaults=True)
        return Q(**dict_params)

    return _filter_dependency


def search_qs_by_fields_dependency(search_fields: list[str]):
    def _search_dependency(search: Optional[str] = Query(
        default=None,
        description='Search by specified fields via this parameter'
    )):
        if not search:
            return Q()
        filters = (Q(**{f'{f_name}__icontains': search}) for f_name in search_fields)
        return reduce(or_, filters)

    return _search_dependency
