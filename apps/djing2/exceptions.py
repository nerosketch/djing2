from djing2.lib import LogicError
from fastapi import HTTPException
from starlette import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler
from rest_framework.response import Response


class UniqueConstraintIntegrityError(APIException):
    status_code = 409
    default_detail = "The request could not be completed due to a conflict with the current state of the resource"
    default_code = "unique_conflict"


class ModelValidationError(HTTPException):
    def __init__(
        self,
        status_code=status.HTTP_400_BAD_REQUEST,
        detail='ModelValidationError'
    ):
        super(ModelValidationError, self).__init__(
            status_code=status_code,
            detail=detail
        )


# TODO: deprecated. Only for Django Rest Framework
def catch_logic_error(exc, context):
    try:
        response = exception_handler(exc, context)
        return response
    except LogicError as err:
        return Response(
            data=str(err),
            status=status.HTTP_400_BAD_REQUEST
        )
