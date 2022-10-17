from typing import Type, Optional, Union, Any, Callable, OrderedDict as OrderedDictType

from django.db.models import QuerySet, Model
from django.db.utils import IntegrityError
from fastapi.params import Depends
from pydantic import BaseModel
from fastapi import HTTPException, Request, APIRouter
from fastapi.types import DecoratedCallable
from starlette import status

from ._fields_cache import build_model_and_schema_fields
from .perms import permission_check_dependency
from .types import DEPENDENCIES, IListResponse, Pagination, NOT_FOUND
from .utils import schema_factory, format_object
from .pagination import paginate_qs_path_decorator


def _generate_perm_dep(qs: QuerySet, route: Union[bool, DEPENDENCIES], perm_prefix: str) -> list[Depends]:
    model = qs.model
    _perm_codename = f"{model._meta.app_label}.{perm_prefix}_{model._meta.object_name.lower()}"
    _dep = Depends(permission_check_dependency(
        perm_codename=_perm_codename
    ))
    if isinstance(route, list):
        new_create_route = route + [_dep]
    elif isinstance(route, tuple):
        new_create_route = list(route) + [_dep]
    else:
        new_create_route = [_dep]
    return new_create_route


class CRUDReadGenerator(APIRouter):
    schema: Type[BaseModel]
    _field_objects: OrderedDictType
    _computed_field_objects: OrderedDictType

    def __init__(
        self,
        schema: Type[BaseModel],
        queryset: QuerySet,
        get_all_route: Union[bool, DEPENDENCIES] = True,
        get_one_route: Union[bool, DEPENDENCIES] = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        self.schema = schema
        self._pk: str = self._pk if hasattr(self, "_pk") else "id"

        self._queryset = queryset

        fo, cfo = build_model_and_schema_fields(self.schema, queryset.model)
        self._field_objects = fo
        self._computed_field_objects = cfo

        # prefix = str(prefix if prefix else self.schema.__name__).lower()
        # prefix = self._base_path + prefix.strip("/")
        # tags = tags or [prefix.strip("/").capitalize()]

        if get_one_route:
            get_one_route = _generate_perm_dep(
                qs=self._queryset,
                route=get_one_route,
                perm_prefix='view'
            )
            self._add_api_route(
                "/{item_id}/",
                self._get_one(),
                methods=["GET"],
                response_model=self.schema,
                summary="Get One",
                dependencies=get_one_route,
                error_responses=[NOT_FOUND],
            )

        if get_all_route:
            get_all_route = _generate_perm_dep(
                qs=self._queryset,
                route=get_all_route,
                perm_prefix='view'
            )
            self._add_api_route(
                "/",
                self._get_all(),
                methods=["GET"],
                response_model=Optional[IListResponse[self.schema]],  # type: ignore
                summary="Get All",
                dependencies=get_all_route,
            )

    def remove_api_route(self, path: str, methods: list[str]) -> None:
        methods_ = set(methods)

        for route in self.routes:
            if (
                route.path == f"{self.prefix}{path}"  # type: ignore
                and route.methods == methods_  # type: ignore
            ):
                self.routes.remove(route)

    def api_route(
        self, path: str, *args: Any, **kwargs: Any
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        """Overrides and exiting route if it exists"""
        methods = kwargs["methods"] if "methods" in kwargs else ["GET"]
        self.remove_api_route(path, methods)
        return super().api_route(path, *args, **kwargs)

    def _add_api_route(
        self,
        path: str,
        endpoint: Callable[..., Any],
        dependencies: Union[bool, DEPENDENCIES],
        error_responses: Optional[list[HTTPException]] = None,
        **kwargs: Any,
    ) -> None:
        dependencies = [] if isinstance(dependencies, bool) else dependencies
        responses: Any = (
            {err.status_code: {"detail": err.detail} for err in error_responses}
            if error_responses
            else None
        )

        super().add_api_route(
            path, endpoint, dependencies=dependencies, responses=responses, **kwargs
        )

    @classmethod
    def get_routes(cls) -> list[str]:
        return ["get_all", "get_one"]

    def get(
        self, path: str, *args: Any, **kwargs: Any
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        self.remove_api_route(path, ["Get"])
        return super().get(path, *args, **kwargs)

    def _get_one(self, *args: Any, **kwargs: Any):
        def route(item_id: int, request: Request) -> OrderedDictType:
            qs = self.filter_qs(request=request)
            try:
                obj = qs.get(pk=item_id)
                return format_object(
                    model_item=obj,
                    field_objects=self._field_objects,
                    computed_field_objects=self._computed_field_objects,
                )
            except qs.model.DoesNotExist:
                raise NOT_FOUND from None
        return route

    def _get_all(self, *args: Any, **kwargs: Any):
        @paginate_qs_path_decorator(
            schema=self.schema,
            db_model=self._queryset.model
        )
        def route(
            request: Request,
            pagination: Pagination = Depends(),
        ):
            qs = self.filter_qs(request=request)
            return qs

        return route

    def filter_qs(self, request: Request, qs: Optional[QuerySet] = None) -> QuerySet[Model]:
        if qs is None:
            qs = self._queryset
        return qs


class CrudRouter(CRUDReadGenerator):
    create_schema: Type[BaseModel]
    update_schema: Type[BaseModel]
    _base_path: str = "/"
    _queryset: QuerySet

    def __init__(
        self,
        schema: Type[BaseModel],
        queryset: QuerySet,
        create_schema: Optional[Type[BaseModel]] = None,
        update_schema: Optional[Type[BaseModel]] = None,
        # prefix: Optional[str] = None,
        tags: Optional[list[str]] = None,
        get_all_route: Union[bool, DEPENDENCIES] = True,
        get_one_route: Union[bool, DEPENDENCIES] = True,
        create_route: Union[bool, DEPENDENCIES] = True,
        update_route: Union[bool, DEPENDENCIES] = True,
        delete_one_route: Union[bool, DEPENDENCIES] = True,
        **kwargs: Any
    ) -> None:
        super().__init__(
            schema=schema,
            # prefix=prefix,
            queryset=queryset,
            tags=tags,
            get_all_route=get_all_route,
            get_one_route=get_one_route,
            **kwargs
        )

        self.create_schema = (
            create_schema
            if create_schema
            else schema_factory(schema, pk_field_name=self._pk, name="Create")
        )
        self.update_schema = (
            update_schema
            if update_schema
            else schema_factory(schema, pk_field_name=self._pk, name="Update")
        )

        if update_route:
            update_route = _generate_perm_dep(
                qs=self._queryset,
                route=update_route,
                perm_prefix='change'
            )
            self._add_api_route(
                "/{item_id}/",
                self._update(),
                methods=["PATCH"],
                response_model=self.schema,
                summary="Update One",
                dependencies=update_route,
                error_responses=[NOT_FOUND],
            )
        if delete_one_route:
            delete_one_route = _generate_perm_dep(
                qs=self._queryset,
                route=delete_one_route,
                perm_prefix='delete'
            )
            self._add_api_route(
                "/{item_id}/",
                self._delete_one(),
                methods=["DELETE"],
                response_model=None,
                summary="Delete One",
                dependencies=delete_one_route,
                error_responses=[NOT_FOUND],
                status_code=status.HTTP_204_NO_CONTENT,
            )
        if create_route:
            create_route = _generate_perm_dep(
                qs=self._queryset,
                route=create_route,
                perm_prefix='add'
            )
            self._add_api_route(
                "/",
                self._create(),
                methods=["POST"],
                response_model=self.schema,
                summary="Create One",
                dependencies=create_route,
                status_code=status.HTTP_201_CREATED
            )

    def post(
        self, path: str, *args: Any, **kwargs: Any
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        self.remove_api_route(path, ["POST"])
        return super().post(path, *args, **kwargs)

    def put(
        self, path: str, *args: Any, **kwargs: Any
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        self.remove_api_route(path, ["PUT"])
        return super().put(path, *args, **kwargs)

    def delete(
        self, path: str, *args: Any, **kwargs: Any
    ) -> Callable[[DecoratedCallable], DecoratedCallable]:
        self.remove_api_route(path, ["DELETE"])
        return super().delete(path, *args, **kwargs)

    def _create(self, *args: Any, **kwargs: Any):
        def route(payload: self.create_schema) -> OrderedDictType:
            pdict = payload.dict(
                exclude_unset=True,
                exclude_defaults=True,
                exclude_none=True
            )
            for fname, fobject in self._field_objects.items():
                value = pdict.get(fname)
                if isinstance(value, int):
                    if fobject.is_relation and not fname.endswith('_id'):
                        del pdict[fname]
                        pdict['%s_id' % fname] = value

            model = self._queryset.model
            try:
                obj = model.objects.create(**pdict)
                return format_object(
                    model_item=obj,
                    field_objects=self._field_objects,
                    computed_field_objects=self._computed_field_objects,
                )
            except IntegrityError as err:
                if 'is not present in table' in str(err):
                    raise NOT_FOUND
                raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Integration error")
        return route

    def _update(self, *args: Any, **kwargs: Any):
        def route(item_id: int, model: dict[str, Union[str, int, float]], request: Request) -> OrderedDictType:
            qs = self.filter_qs(request=request)
            model_fields = tuple(fname for fname, _ in model.items())
            update_fields = tuple(fname for fname, _ in self._field_objects.items() if fname in model_fields)
            try:
                obj = qs.get(pk=item_id)
                for fname in update_fields:
                    value = model.get(fname)
                    setattr(obj, fname, value)
                obj.save(update_fields=update_fields)
                return format_object(
                    model_item=obj,
                    field_objects=self._field_objects,
                    computed_field_objects=self._computed_field_objects,
                )
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

    @classmethod
    def get_routes(cls) -> list[str]:
        return super().get_routes() + ["create", "update", "delete_one"]
