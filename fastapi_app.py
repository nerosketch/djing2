#!/usr/bin/env python3

import os
import sys
#  from importlib.util import find_spec
from django.apps import apps
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware

sys.path.insert(0, os.path.abspath("apps"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.djing2.settings")
apps.populate(settings.INSTALLED_APPS)

from apps.addresses.views import router
from djing2.lib.fastapi.auth import TokenAPIKeyHeader

token_auth_dep = TokenAPIKeyHeader(name='Authorization')


def get_application() -> FastAPI:
    # Main Fast API application
    app = FastAPI(
        title='djing2',
        openapi_url="/api/openapi.json",
        debug=settings.DEBUG,
        dependencies=[Depends(token_auth_dep)]
    )

    # Set all CORS enabled origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.ALLOWED_HOSTS or []] or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include all api endpoints
    app.include_router(router, prefix='/api')

    application = get_wsgi_application()
    # Mounts an independent web URL for Django WSGI application
    app.mount("/", WSGIMiddleware(application))

    return app


app = get_application()


@app.middleware('http')
def x_real_ip_middleware(request: Request, call_next):
    real_ip = request.headers.get('HTTP_X_REAL_IP')
    if real_ip is not None:
        request.headers['REMOTE_ADDR'] = real_ip
    response = call_next(request)
    return response


#  from fastapi.staticfiles import StaticFiles
#  from api import router
# os.environ.setdefault("DJANGO_CONFIGURATION", "Localdev")
# app = FastAPI()
# app.mount("/admin", WSGIMiddleware(application))
# app.mount("/static",
#     StaticFiles(
#          directory=os.path.normpath(
#               os.path.join(find_spec("django.contrib.admin").origin, "..", "static")
#          )
#    ),
#    name="static",
# )
# app.include_router(router)
