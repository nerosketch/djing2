from typing import TypeVar, Optional, Sequence, Generic, OrderedDict as OrderedDictType

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field as PydanticField
from pydantic.generics import GenericModel
from starlette import status
from django.db.models import Field as DjangoField


PYDANTIC_SCHEMA = BaseModel
MAX_LIMIT = 1000
DEFAULT_LIMIT = 60

T = TypeVar("T", bound=BaseModel)
DEPENDENCIES = Optional[Sequence[Depends]]


class IListResponse(GenericModel, Generic[T]):
    count: int
    next: Optional[str]
    previous: Optional[str]
    results: list[T]


# TODO: split fields into separate code
class Pagination(BaseModel):
    page: int = 1
    page_size: int = PydanticField(DEFAULT_LIMIT, lt=MAX_LIMIT+1, gt=0)
    fields: Optional[str] = None
    ordering: Optional[str] = PydanticField(None, regex=r'^-?\w{1,50}$')


FIELD_OBJECTS_TYPE = OrderedDictType[str, DjangoField]
COMPUTED_FIELD_OBJECTS_TYPE = OrderedDictType[str, PydanticField]


class OrmConf:
    orm_mode = True


NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
