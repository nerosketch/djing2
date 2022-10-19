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

sys.path.insert(0, os.path.abspath("apps"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.djing2.settings")
apps.populate(settings.INSTALLED_APPS)

from djing2.routers import router
from djing2.lib.logger import logger
from djing2.lib.fastapi.pika_client import PikaClient


class MainApp(FastAPI):
    pika_client: PikaClient

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pika_client = PikaClient(self.log_incoming_message)

    @classmethod
    def log_incoming_message(cls, message: dict):
        """Method to do something meaningful with the incoming message"""
        logger.info('Here we got incoming message %s', message)


def get_application() -> MainApp:
    # Main Fast API application
    _app = MainApp(
        title='djing2',
        openapi_url="/api/openapi.json",
        debug=settings.DEBUG,
        swagger_ui_parameters={"docExpansion": "none"},
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

    _django_app = get_asgi_application()
    # Mounts an independent web URL for Django WSGI application
    _app.mount("/", _django_app)

    return _app


app = get_application()


@app.on_event('startup')
async def run_pika_on_startup():
    loop = asyncio.get_running_loop()
    task = loop.create_task(app.pika_client.consume(loop))
    await task


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
