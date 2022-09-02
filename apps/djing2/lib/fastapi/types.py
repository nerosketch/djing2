from typing import Dict, TypeVar, Optional, Sequence, Generic, List

from fastapi.params import Depends
from pydantic import BaseModel
from pydantic.generics import GenericModel

PAGINATION = Dict[str, Optional[int]]
PYDANTIC_SCHEMA = BaseModel

T = TypeVar("T", bound=BaseModel)
DEPENDENCIES = Optional[Sequence[Depends]]


class IListResponse(GenericModel, Generic[T]):
    count: int
    next: Optional[str]
    previous: Optional[str]
    results: List[T]
