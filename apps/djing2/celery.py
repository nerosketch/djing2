import os
from celery import Celery
from fastapi_redis_cache import FastApiRedisCache

redis_cache = FastApiRedisCache()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djing2.settings')
app = Celery('djing2')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()
