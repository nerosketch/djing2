from typing import Union, Optional
from fastapi import Query, Depends, Request
from django.db.models.query import QuerySet
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


def filter_qs_by_fields_decorator(qs: QuerySet, fields: dict[str, type]):
    model = qs.model
    prms = {f_name: (Optional[int], None) for f_name, f_type in fields.items()}
    query_model = create_model(f'{model}FieldFilterSchema', **prms)

    def _filter_dependency(request: Request, params: query_model = Depends()) -> QuerySet:
        dict_params = params.dict(exclude_none=True, exclude_unset=True, exclude_defaults=True)
        filter_args = {f_name: request.get(f_name, None) for f_name, f_val in dict_params.items()}
        q = qs.filter(**filter_args)
        return q

    return _filter_dependency
