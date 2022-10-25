import time
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import FastAPI, Request


# TODO: deprecated, defined in 'fastapi_app.py'
class XRealIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        real_ip = request.META.get('HTTP_X_REAL_IP')
        if real_ip is not None:
            request.META['REMOTE_ADDR'] = real_ip
        return self.get_response(request)


async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


def apply_middlewares(app: FastAPI):
    app.add_middleware(BaseHTTPMiddleware, dispatch=add_process_time_header)
