from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.http.response import Http404
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette import status


def django_http_resp_404_handler(request: Request, exc: Http404):
    return JSONResponse(
        content=str(exc),
        status_code=status.HTTP_404_NOT_FOUND
    )


def django_validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        content=str(exc.message_dict['__all__'][0]),
        status_code=status.HTTP_400_BAD_REQUEST
    )


def django_IntegrityError_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        content=str(exc),
        status_code=status.HTTP_409_CONFLICT
    )
