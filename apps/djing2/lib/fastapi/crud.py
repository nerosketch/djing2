from typing import Type, Optional, List, Union, Any
from collections import OrderedDict
from django.db.models import QuerySet, Model
from django.db.utils import IntegrityError
from fastapi import HTTPException, status
from ._crud_generator import CRUDGenerator, NOT_FOUND
from ._types import DEPENDENCIES, PAGINATION, PYDANTIC_SCHEMA as SCHEMA


class DjangoCrudRouter(CRUDGenerator[SCHEMA]):
    _queryset: QuerySet
    _field_objects: OrderedDict

    def __init__(
        self,
        schema: Type[SCHEMA],
        queryset: QuerySet,
        create_schema: Optional[Type[SCHEMA]] = None,
        update_schema: Optional[Type[SCHEMA]] = None,
        prefix: Optional[str] = None,
        tags: Optional[List[str]] = None,
        #  paginate: Optional[int] = None,
        get_all_route: Union[bool, DEPENDENCIES] = True,
        get_one_route: Union[bool, DEPENDENCIES] = True,
        create_route: Union[bool, DEPENDENCIES] = True,
        update_route: Union[bool, DEPENDENCIES] = True,
        delete_one_route: Union[bool, DEPENDENCIES] = True,
        **kwargs: Any
    ) -> None:
        schema_fields = schema.__fields__
        model = queryset.model
        field_objects = OrderedDict((fname, model._meta.get_field(fname)) for fname, _ in schema_fields.items())
        self._field_objects = field_objects
        self._queryset = queryset

        super().__init__(
            schema=schema,
            create_schema=create_schema,
            update_schema=update_schema,
            prefix=prefix,
            tags=tags,
            paginate=1000,
            get_all_route=get_all_route,
            get_one_route=get_one_route,
            create_route=create_route,
            update_route=update_route,
            delete_one_route=delete_one_route,
            **kwargs
        )

    def paginate(self, qs: QuerySet[Model], skip: Optional[int], limit: Optional[int]) -> QuerySet[Model]:
        if skip is not None:
            qs = qs[int(skip):]

        if limit is not None:
            qs = qs[:int(limit)]

        return qs

    def filter_qs(self, qs: Optional[QuerySet] = None) -> QuerySet[Model]:
        if qs is None:
            qs = self._queryset
        return qs.all()

    def format_object(self, model_item: Model) -> OrderedDict:
        return OrderedDict(
            (fname, fobject.value_from_object(model_item)) for fname, fobject in self._field_objects.items()
        )

    def _get_all(self, *args: Any, **kwargs: Any):
        def route(
            pagination: PAGINATION = self.pagination,
        ) -> List[OrderedDict]:
            skip, limit = pagination.get("skip"), pagination.get("limit")

            qs = self.filter_qs()
            qs = self.paginate(qs=qs, skip=skip, limit=limit)

            return [self.format_object(m) for m in qs]

        return route

    def _get_one(self, *args: Any, **kwargs: Any):
        def route(item_id: int) -> OrderedDict:
            qs = self.filter_qs()
            try:
                obj = qs.get(pk=item_id)
                return self.format_object(obj)
            except qs.model.DoesNotExist:
                raise NOT_FOUND from None
        return route

    def _create(self, *args: Any, **kwargs: Any):
        def route(payload: self.create_schema) -> OrderedDict:
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
        def route(item_id: int, model: dict[str, Union[str, int, float]]) -> OrderedDict:
            qs = self.filter_qs()
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
