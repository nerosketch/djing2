import logging
from threading import Thread
from datetime import datetime
import requests
from django.contrib.contenttypes.models import ContentType
from rest_framework.serializers import ModelSerializer
from uwsgi_tasks import task, TaskExecutor, SPOOL_OK, SPOOL_RETRY

from webhooks.models import HookObserver


def _model_instance_to_dict(instance, model_class) -> dict:
    class _model_serializer(ModelSerializer):
        class Meta:
            model = model_class
            fields = '__all__'
    ser = _model_serializer(instance=instance)
    return ser.data


def _send_notify(url: str, notification_type: int, ct: ContentType, model_class, instance=None):
    data = {
        'nt': notification_type,
        'ct': {
            'app': ct.app_label,
            'model': ct.model
        },
        'inst': _model_instance_to_dict(instance=instance, model_class=model_class) if instance else None,
        'time': datetime.now().strftime('%Y.%m.%dT%H:%M:%s')
    }
    r = requests.post(url, data=data)
    return r.content


@task(executor=TaskExecutor.SPOOLER, spooler_return=True, retry_timeout=15)
def send_update2observers(notification_type: int, instance_id, app_label: str, model: str):
    ct = ContentType.objects.get_by_natural_key(
        app_label=app_label,
        model=model
    )
    model_class = ct.model_class()
    if model_class is None:
        logging.warning('send_update2observers() model_class is None')
        return SPOOL_RETRY
    if instance_id is None:
        objects_instance = None
    else:
        objects_instance = model_class.objects.filter(pk=instance_id).first()
        if objects_instance is None:
            logging.warning('Object instance is none, pk="%s", model="%s"' % (instance_id or 0, model_class))
            return SPOOL_OK

    thrs = []
    for observer in HookObserver.objects.filter(
        content_type=ct,
        notification_type=int(notification_type)
    ).iterator():
        args = {
            'url': str(observer.client_url),
            'instance': objects_instance,
            'notification_type': int(notification_type),
            'model_class': model_class,
            'ct': ct,
        }
        thr = Thread(target=_send_notify, kwargs=args)
        thr.start()
        thrs.append(thr)
    for thr in thrs:
        thr.join(timeout=15)
    return SPOOL_OK
