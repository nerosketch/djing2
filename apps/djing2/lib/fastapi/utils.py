from typing import Type, Optional, OrderedDict as OrderedDictType, Any
from collections import OrderedDict

from fastapi import APIRouter
from pydantic import create_model, BaseModel
from django.db.models import Model

from .types import T, FIELD_OBJECTS_TYPE, COMPUTED_FIELD_OBJECTS_TYPE


def schema_factory(
    schema_cls: Type[T], pk_field_name: str = "id", name: str = "Create"
) -> Type[T]:
    """
    Is used to create a CreateSchema which does not contain pk
    """

    fields = {
        f.name: (f.type_, ...)
        for f in schema_cls.__fields__.values()
        if f.name != pk_field_name
    }

    name = schema_cls.__name__ + name
    schema: Type[T] = create_model(__model_name=name, **fields)  # type: ignore
    return schema


def format_object(
    model_item: Model,
    field_objects: FIELD_OBJECTS_TYPE,
    computed_field_objects: COMPUTED_FIELD_OBJECTS_TYPE,
    fields_list: Optional[list[str]] = None
) -> OrderedDictType:
    result_dict_dields = (
        (fname, fobject.value_from_object(model_item)) for fname, fobject in field_objects.items()
    )
    if fields_list is not None:
        if not isinstance(fields_list, (list, tuple, set)):
            raise ValueError('fields_list must be list, tuple or set: %s' % fields_list)
        result_dict_dields = ((fname, obj) for fname, obj in result_dict_dields if fields_list)
    r = OrderedDict(result_dict_dields)
    r.update({
        fname: getattr(model_item, fname, None) for fname, ob in computed_field_objects.items()
    })
    return r


def get_initial(schema: Type[BaseModel]) -> dict:
    return {fname: field.default for fname, field in schema.__fields__.items() if field.default}


def create_get_initial_route(router: APIRouter, schema: Type[BaseModel], path: str = '/get_initial/'):
    @router.get(path)
    def get_initial_values():
        return get_initial(schema)
    return get_initial_values
