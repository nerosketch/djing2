from typing import Type, Optional, OrderedDict as OrderedDictType
from collections import OrderedDict

from fastapi import APIRouter
from pydantic import create_model, BaseModel
from pydantic.main import ModelMetaclass
from django.db.models import Model
from django.shortcuts import get_object_or_404 as _get_object_or_404
from django.core.exceptions import ValidationError

from .types import T, FIELD_OBJECTS_TYPE, COMPUTED_FIELD_OBJECTS_TYPE, NOT_FOUND


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
    result_dict_fields = (
        (fname, fobject.value_from_object(model_item)) for fname, fobject in field_objects.items()
    )

    if fields_list:
        if not isinstance(fields_list, (list, tuple, set)):
            raise ValueError('fields_list must be list, tuple or set: %s' % fields_list)
        result_dict_fields = (
            (fname, val) for fname, val in result_dict_fields if val is not None and fname in fields_list
        )

    r = OrderedDict(result_dict_fields)
    if computed_field_objects:
        computed_field_objects_keys = computed_field_objects.keys()
        if fields_list:
            computed_field_objects_keys = (fname for fname in computed_field_objects_keys if fname in fields_list)
        r.update({
            fname: getattr(model_item, fname, None) for fname in computed_field_objects_keys
        })

    return r


def get_initial(schema: Type[BaseModel]) -> dict:
    def _get_default(field):
        d = field.default
        df = field.default_factory
        if not d and df:
            d = df()
        return d
    gen = ((fname, _get_default(field)) for fname, field in schema.__fields__.items())
    return {fname: val for fname, val in gen if val}


def create_get_initial_route(router: APIRouter, schema: Type[BaseModel], path: str = '/get_initial/'):
    @router.get(path)
    def get_initial_values():
        return get_initial(schema)
    return get_initial_values


def get_object_or_404(queryset, *filter_args, **filter_kwargs):
    """
    Same as Django's standard shortcut, but make sure to also raise 404
    if the filter_kwargs don't match the required types.
    """
    try:
        return _get_object_or_404(queryset, *filter_args, **filter_kwargs)
    except (TypeError, ValueError, ValidationError):
        raise NOT_FOUND


class AllOptionalMetaclass(ModelMetaclass):
    """Makes Pydantic model fields optional"""

    def __new__(mcs, name, bases, namespaces, **kwargs):
        annotations = namespaces.get('__annotations__', {})
        for base in bases:
            annotations.update(base.__annotations__)
        for field in annotations:
            if not field.startswith('__'):
                annotations[field] = Optional[annotations[field]]
        namespaces['__annotations__'] = annotations

        return super().__new__(mcs, name, bases, namespaces, **kwargs)
