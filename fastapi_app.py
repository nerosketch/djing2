#!/usr/bin/env python3

import os
import sys
import asyncio
#  from importlib.util import find_spec
from django.apps import apps
from django.conf import settings
from django.core.asgi import get_asgi_application
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import ORJSONResponse

sys.path.insert(0, os.path.abspath("apps"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.djing2.settings")
apps.populate(settings.INSTALLED_APPS)

from djing2.routers import router
from djing2.lib.fastapi.amqp_client import AmqpProxyClient
from djing2.lib.fastapi.http_exceptions import handler_pairs


class MainApp(FastAPI):
    amqp_client: AmqpProxyClient

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.amqp_client = AmqpProxyClient()


def get_application() -> MainApp:
    # Main Fast API application
    _app = MainApp(
        title='djing2',
        openapi_url="/api/openapi.json",
        debug=settings.DEBUG,
        swagger_ui_parameters={"docExpansion": "none"},
        # default_response_class=ORJSONResponse
    )

    # Set all CORS enabled origins
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.ALLOWED_HOSTS or []] or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include all api endpoints
    _app.include_router(router)

    for handler, exc in handler_pairs:
        _app.add_exception_handler(exc, handler)

    _django_app = get_asgi_application()
    # Mounts an independent web URL for Django WSGI application
    _app.mount("/", _django_app)

    return _app


app = get_application()


@app.on_event('startup')
async def amqp_pika_on_startup():
    loop = asyncio.get_running_loop()
    await loop.create_task(app.amqp_client.a_init())
    await loop.create_task(app.amqp_client.consume())


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
