from typing import Type
from collections import OrderedDict

from pydantic import BaseModel
from django.db.models import Model
from django.core.exceptions import FieldDoesNotExist
from .types import COMPUTED_FIELD_OBJECTS_TYPE, FIELD_OBJECTS_TYPE


_db_model_cache_map = {}
_schema_cache_map = {}


def build_model_and_schema_fields(schema: Type[BaseModel], db_model: Type[Model]) -> tuple[
    FIELD_OBJECTS_TYPE, COMPUTED_FIELD_OBJECTS_TYPE
]:
    """
    Build model fields and computed fields
    """
    # global _db_model_cache_map, _schema_cache_map
    schema_fields = schema.__fields__

    field_objects = _db_model_cache_map.get(db_model, {})
    computed_field_objects = _schema_cache_map.get(schema, {})
    if all([field_objects, computed_field_objects]):
        return field_objects, computed_field_objects

    for fname, schema_field in schema_fields.items():
        try:
            field_objects[fname] = db_model._meta.get_field(fname)
        except FieldDoesNotExist:
            computed_field_objects[fname] = schema_field

    _field_objects = OrderedDict(field_objects)
    _computed_field_objects = OrderedDict(computed_field_objects)
    _db_model_cache_map[db_model] = _field_objects
    _schema_cache_map[schema] = _computed_field_objects
    return _field_objects, _computed_field_objects
