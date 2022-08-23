import os
from celery import Celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djing2.settings')
app = Celery('djing2', broker='pyamqp://guest@localhost/')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
