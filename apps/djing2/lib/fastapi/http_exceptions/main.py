from django.http.response import Http404
from djing2.lib import LogicError
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette import status


def catch_logic_error(request: Request, exc: LogicError):
    return JSONResponse(
        content=str(exc),
        status_code=status.HTTP_400_BAD_REQUEST
    )


def django_http_resp_404_handler(request: Request, exc: Http404):
    return JSONResponse(
        content=str(exc),
        status_code=status.HTTP_404_NOT_FOUND
    )
