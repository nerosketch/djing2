from django.http.response import Http404
from fastapi import Request
from fastapi.responses import JSONResponse


def django_http_resp_404_handler(request: Request, exc: Http404):
    return JSONResponse(
        content=str(exc),
        status_code=404
    )
