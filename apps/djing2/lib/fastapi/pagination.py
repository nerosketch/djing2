from functools import wraps
from typing import Optional, Type

from fastapi import Request, Depends
from django.db.models import QuerySet, Model

from ._fields_cache import build_model_and_schema_fields
from .types import (
    Pagination,
    PYDANTIC_SCHEMA,
    IListResponse,
    DEFAULT_LIMIT
)
from .utils import format_object


def paginate_qs(qs: QuerySet[Model], page: Optional[int], page_size: Optional[int]) -> QuerySet[Model]:
    if not page_size:
        page_size = DEFAULT_LIMIT

    skip = 0
    if page is not None:
        page = int(page)
        if page > 0:
            skip = (page - 1) * page_size

    return qs[skip:page_size + skip]


def get_next_url(r: Request, current_page: int, all_count: int, limit: int) -> Optional[str]:
    left = all_count - limit * current_page
    if left > 0:
        next_page = current_page + 1
        u = r.url
        return str(u.include_query_params(page=next_page))


def get_prev_url(r: Request, current_page: int) -> Optional[str]:
    if current_page > 0:
        page = current_page - 1
        u = r.url
        return str(u.include_query_params(page=page))


def apply_ordering(qs: QuerySet, field_name: str) -> QuerySet:
    if not field_name:
        return qs
    return qs.order_by(field_name)


def paginate_qs_path_decorator(
    schema: Type[PYDANTIC_SCHEMA],
    db_model: Type[Model]
):
    field_objects, computed_field_objects = build_model_and_schema_fields(schema, db_model)

    def _fwrap(fn):
        @wraps(fn)
        def _wrap(
            request: Request,
            pagination: Pagination = Depends(),
            *args, **kwargs
        ):
            qs = fn(request=request, pagination=pagination, *args, **kwargs)
            all_count = qs.count()

            fields_list = None
            if pagination.fields:
                fields_list = pagination.fields.split(',')
                if len(fields_list) > 0:
                    param_fields_list = set(fields_list)
                    model_fields_list = {field_name for field_name, _ in field_objects.items()}
                    fields_list = param_fields_list & model_fields_list
                    # qs = qs.only(*fields_list)
                    # TODO: use computed fields from DRF serializer

            r_qs = paginate_qs(
                qs=qs,
                page=pagination.page,
                page_size=pagination.page_size
            )

            if pagination.ordering:
                r_qs = apply_ordering(qs=r_qs, field_name=pagination.ordering)

            return IListResponse[schema](
                count=all_count,
                next=get_next_url(
                    r=request,
                    current_page=pagination.page,
                    all_count=all_count,
                    limit=pagination.page_size
                ),
                previous=get_prev_url(
                    r=request,
                    current_page=pagination.page
                ),
                results=(format_object(
                    model_item=o,
                    field_objects=field_objects,
                    computed_field_objects=computed_field_objects,
                    fields_list=fields_list,
                ) for o in r_qs)
            )

        return _wrap
    return _fwrap
