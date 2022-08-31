from typing import Type, Optional, List, Union, Any, Dict, OrderedDict as OrderedDictType
from collections import OrderedDict

from django.core.exceptions import FieldDoesNotExist
from django.db.models import QuerySet, Model
from django.db.utils import IntegrityError
from djing2.lib.fastapi._types import IListResponse
from fastapi import HTTPException, status, Request

from ._crud_generator import CRUDGenerator, NOT_FOUND
from ._types import DEPENDENCIES, PAGINATION, PYDANTIC_SCHEMA as SCHEMA


class DjangoCrudRouter(CRUDGenerator[SCHEMA]):
    _queryset: QuerySet
    _field_objects: OrderedDictType
    _computed_field_objects: OrderedDictType

    def __init__(
        self,
        schema: Type[SCHEMA],
        queryset: QuerySet,
        create_schema: Optional[Type[SCHEMA]] = None,
        update_schema: Optional[Type[SCHEMA]] = None,
        # prefix: Optional[str] = None,
        tags: Optional[List[str]] = None,
        # paginate: Optional[int] = None,
        get_all_route: Union[bool, DEPENDENCIES] = True,
        get_one_route: Union[bool, DEPENDENCIES] = True,
        create_route: Union[bool, DEPENDENCIES] = True,
        update_route: Union[bool, DEPENDENCIES] = True,
        delete_one_route: Union[bool, DEPENDENCIES] = True,
        **kwargs: Any
    ) -> None:
        schema_fields = schema.__fields__
        model = queryset.model
        self._queryset = queryset

        # Build model fields and computed fields
        field_objects = {}
        computed_field_objects = {}
        for fname, schema_field in schema_fields.items():
            try:
                field_objects[fname] = model._meta.get_field(fname)
            except FieldDoesNotExist:
                computed_field_objects[fname] = schema_field
        self._field_objects = OrderedDict(field_objects)
        self._computed_field_objects = OrderedDict(computed_field_objects)

        super().__init__(
            schema=schema,
            create_schema=create_schema,
            update_schema=update_schema,
            # prefix=prefix,
            tags=tags,
            paginate=100,
            get_all_route=get_all_route,
            get_one_route=get_one_route,
            create_route=create_route,
            update_route=update_route,
            delete_one_route=delete_one_route,
            **kwargs
        )

    @staticmethod
    def paginate(qs: QuerySet[Model], page: Optional[int], page_size: Optional[int]) -> QuerySet[Model]:
        if not page_size:
            page_size = 100

        skip = 0
        if page is not None:
            page = int(page)
            if page > 0:
                skip = (page - 1) * page_size

        return qs[skip:page_size+skip]

    def filter_qs(self, request: Request, qs: Optional[QuerySet] = None) -> QuerySet[Model]:
        if qs is None:
            qs = self._queryset
        return qs

    def format_object(self, model_item: Model, fields_list: Optional[List[str]] = None) -> OrderedDictType:
        object_fields = (
            (fname, fobject.value_from_object(model_item)) for fname, fobject in self._field_objects.items()
        )
        if fields_list is not None:
            if not isinstance(fields_list, (list, tuple, set)):
                raise ValueError('fields_list must be list, tuple or set: %s' % fields_list)
            object_fields = ((fname, obj) for fname, obj in object_fields if fields_list)
        r = OrderedDict(object_fields)
        r.update({
            fname: getattr(model_item, fname, None) for fname, ob in self._computed_field_objects.items()
        })
        return r

    @staticmethod
    def get_next_url(r: Request, current_page: int, all_count: int, limit: int) -> Optional[str]:
        left = all_count - limit * current_page
        if left > 0:
            next_page = current_page + 1
            u = r.url
            return str(u.include_query_params(page=next_page))

    @staticmethod
    def get_prev_url(r: Request, current_page: int) -> Optional[str]:
        if current_page > 0:
            page = current_page - 1
            u = r.url
            return str(u.include_query_params(page=page))

    def _get_all(self, *args: Any, **kwargs: Any):
        def route(
            request: Request,
            pagination: PAGINATION = self.pagination,
            fields: Optional[str] = None,
        ) -> IListResponse[self.schema]:

            page, page_size = pagination.get("page"), pagination.get("page_size")
            if not page_size or page_size == 0:
                page_size = 100

            qs = self.filter_qs(request=request)
            all_count = qs.count()

            fields_list = None
            if fields:
                fields_list = fields.split(',')
                if len(fields_list) > 0:
                    param_fields_list = set(fields_list)
                    model_fields_list = {field_name for field_name, _ in self._field_objects.items()}
                    fields_list = param_fields_list & model_fields_list
                    qs = qs.only(*fields_list)
                    # TODO: use computed fields from DRF serializer

            qs = self.paginate(qs=qs, page=page, page_size=page_size)
            return IListResponse[self.schema](
                count=all_count,
                next=self.get_next_url(r=request, current_page=page, all_count=all_count, limit=page_size),
                previous=self.get_prev_url(r=request, current_page=page),
                results=[self.format_object(m, fields_list) for m in qs]
            )

        return route

    def _get_one(self, *args: Any, **kwargs: Any):
        def route(item_id: int, request: Request) -> OrderedDictType:
            qs = self.filter_qs(request=request)
            try:
                obj = qs.get(pk=item_id)
                return self.format_object(obj)
            except qs.model.DoesNotExist:
                raise NOT_FOUND from None
        return route

    def _create(self, *args: Any, **kwargs: Any):
        def route(payload: self.create_schema) -> OrderedDictType:
            pdict = payload.dict()
            for fname, fobject in self._field_objects.items():
                value = pdict.get(fname)
                if isinstance(value, int):
                    if fobject.is_relation:
                        del pdict[fname]
                        pdict['%s_id' % fname] = value

            model = self._queryset.model
            try:
                obj = model.objects.create(**pdict)
                return self.format_object(obj)
            except IntegrityError as err:
                if 'is not present in table' in str(err):
                    raise NOT_FOUND
                raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Integration error")
        return route

    def _update(self, *args: Any, **kwargs: Any):
        def route(item_id: int, model: Dict[str, Union[str, int, float]], request: Request) -> OrderedDictType:
            qs = self.filter_qs(request=request)
            model_fields = tuple(fname for fname, _ in model.items())
            update_fields = tuple(fname for fname, _ in self._field_objects.items() if fname in model_fields)
            try:
                obj = qs.get(pk=item_id)
                for fname in update_fields:
                    value = model.get(fname)
                    setattr(obj, fname, value)
                obj.save(update_fields=update_fields)
                return self.format_object(obj)
            except qs.model.DoesNotExist:
                raise NOT_FOUND from None
        return route

    def _delete_one(self, *args: Any, **kwargs: Any):
        def route(item_id: int) -> None:
            model = self._queryset.model
            rq = model.objects.filter(pk=item_id)
            if not rq.exists():
                raise NOT_FOUND
            rq.delete()
            return None
        return route

    @staticmethod
    def get_routes() -> List[str]:
        return ["get_all", "create", "get_one", "update", "delete_one"]
