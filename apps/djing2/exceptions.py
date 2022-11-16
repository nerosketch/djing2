from fastapi import HTTPException
from starlette import status
from rest_framework.exceptions import APIException


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
