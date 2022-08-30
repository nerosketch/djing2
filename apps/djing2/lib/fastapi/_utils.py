from typing import Optional, Type, Any

from fastapi import Depends, HTTPException
from pydantic import create_model

from ._types import T, PAGINATION


# class AttrDict(dict):  # type: ignore
#     def __init__(self, *args, **kwargs) -> None:  # type: ignore
#         super(AttrDict, self).__init__(*args, **kwargs)
#         self.__dict__ = self


# def get_pk_type(schema: Type[PYDANTIC_SCHEMA], pk_field: str) -> Any:
#     try:
#         return schema.__fields__[pk_field].type_
#     except KeyError:
#         return int


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


def create_query_validation_exception(field: str, msg: str) -> HTTPException:
    return HTTPException(
        422,
        detail={
            "detail": [
                {"loc": ["query", field], "msg": msg, "type": "type_error.integer"}
            ]
        },
    )


def pagination_factory(max_limit: Optional[int] = None) -> Any:
    """
    Created the pagination dependency to be used in the router
    """

    def pagination(page: int = 0, page_size: Optional[int] = 100) -> PAGINATION:
        if page < 0:
            raise create_query_validation_exception(
                field="page",
                msg="page query parameter must be greater or equal to zero",
            )

        if page_size is not None:
            if page_size <= 0:
                raise create_query_validation_exception(
                    field="page_size", msg="page_size query parameter must be greater then zero"
                )

            elif max_limit and max_limit < page_size:
                raise create_query_validation_exception(
                    field="page_size",
                    msg=f"page_size query parameter must be less then {max_limit}",
                )

        return {"page": page, "page_size": page_size}

    return Depends(pagination)
