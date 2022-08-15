from typing import TypeVar, Generic, Type, Callable
from enum import Enum
from pydantic import BaseModel
from django.db.models import QuerySet, Model
from fastapi.routing import APIRouter
from starlette import status

T = TypeVar('T')

class CRUD(Generic[T]):
    queryset: QuerySet
    schema: T

    def filter_queryset(self, queryset: QuerySet):
        return queryset

    def get_queryset(self):
        return self.queryset

    def create(self, body: T) -> Model:
        obj = self.queryset.create(**body)
        return obj

    #@router.get("/test/", tags=["addr"], response_model=schemas.AddressModelSchema)
    #async def new_object(addr_body: schemas.AddressBaseSchema):
    #    """Creating new AddressModel object and return it instance from db"""
    #    return [2,23,4,4,4,89]


#  def crud_decorator(path: str, schema: Type[T], router: APIRouter, tag: Enum) -> Callable[[Type[CRUD[T]]], Type[CRUD[T]]]:
def crud_decorator(path: str, schema: Type[T], router: APIRouter, tag: Enum):
    print('crud_decorator', path, schema, router, tag, type(schema))

    def _wrapped(cls: Type[CRUD[T]]) -> Type[CRUD[T]]:
        print('_wrapped', cls, type(cls))
        #class _crud_class(cls):
        #    def __init__(self, *args, **kwargs):
        #        super().__init__(*args, **kwargs)
        #        # POST, add new object


        def _create(self: CRUD[T], body: Type[T]) -> dict:
            #  return dict(cls.create(self=self, body=body))
            r = super(cls, self).create(body=body)
            print('Create result', r)
            return {'model': 'fields'}

        cls.create = _create
        router.add_api_route(
            path, cls.create,
            response_model=schema,
            tags=[tag],
            methods=['POST'],
            status_code=status.HTTP_201_CREATED
        )

        print('_crud_class', _crud_class, type(_crud_class))
        return _crud_class
    return _wrapped
