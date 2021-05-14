"""
WSGI config for djing2 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application

sys.path.insert(0, os.path.abspath("apps"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djing2.settings")
# os.environ.setdefault('PYTHONUNBUFFERED', '1')

application = get_wsgi_application()
