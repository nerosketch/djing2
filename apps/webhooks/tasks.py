from typing import Optional
from threading import Thread
from datetime import datetime
import requests
from uwsgi_tasks import task, TaskExecutor, SPOOL_OK

from webhooks.models import HookObserver


def _send_notify(url: str, notification_type: int, app_label: str, model_str: str, data: Optional[dict]=None):
    data = {
        'nt': notification_type,
        'ct': {
            'app': app_label,
            'model': model_str
        },
        'time': datetime.now().strftime('%Y.%m.%dT%H:%M:%s')
    }
    r = requests.post(url, data=data)
    return r.content


def _run_task_thread(notification_type: int, app_label: str, model_str: str, data: Optional[dict] = None):
    for observer in HookObserver.objects.filter(
        content_type__app_label=app_label,
        content_type__model=model_str,
        notification_type=int(notification_type)
    ).iterator():
        args = {
            'url': str(observer.client_url),
            'notification_type': int(notification_type),
            'app_label': app_label,
            'model_str': model_str,
            'data': data,
        }
        thr = Thread(target=_send_notify, kwargs=args)
        thr.start()
        yield thr


@task(executor=TaskExecutor.SPOOLER, spooler_return=True, retry_timeout=15)
def send_update2observers_task(notification_type: int, app_label: str, model_str: str, data: Optional[dict] = None):
    for thr in _run_task_thread(notification_type, app_label, model_str, data):
        thr.join(timeout=300)
    return SPOOL_OK
