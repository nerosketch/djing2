from fastapi import HTTPException
from starlette import status
from rest_framework.exceptions import APIException


class UniqueConstraintIntegrityError(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The request could not be completed due to a conflict with the current state of the resource"
    default_code = "unique_conflict"


class BaseProjectError(HTTPException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'Internal server error'

    def __init__(
        self,
        status_code=status_code,
        detail=default_detail
    ):
        super().__init__(
            status_code=status_code or self.status_code,
            detail=detail or self.default_detail
        )


class DuplicationError(BaseProjectError):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'ModelDuplicationError'


class ModelValidationError(BaseProjectError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'ModelValidationError'
