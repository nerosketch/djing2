import socket
from types import FunctionType
from typing import Union, Optional
from time import sleep
from functools import wraps
from contextlib import contextmanager

from celery.utils.log import get_task_logger
from djing2 import celery_app
from celery.local import PromiseProxy

logger = get_task_logger(__name__)

LOCK_EXPIRE = 60 * 10  # Lock expires in 10 minutes

LOCK_FN_TYPE = Optional[Union[FunctionType, str]]


class ProcessLocked(OSError):
    """only one process for function"""


@contextmanager
def process_lock_cm(lock_name: LOCK_FN_TYPE = None, wait=False):
    s = None
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        # Create an abstract socket, by prefixing it with null.
        if callable(lock_name):
            really_lock_name = lock_name()
        else:
            really_lock_name = str(lock_name)
        if wait:
            while True:
                try:
                    s.bind('\0djing2_lock_%s' % really_lock_name)
                    break
                except OSError as err:
                    sleep(0.2)
        else:
            s.bind('\0djing2_lock_%s' % really_lock_name)
        yield s
    except OSError as err:
        raise ProcessLocked from err
    finally:
        if s is not None:
            s.close()


def process_lock_decorator(lock_name: LOCK_FN_TYPE = None, wait=False):
    def process_lock_wrap(fn):
        @wraps(fn)
        def _wrapped(*args, **kwargs):
            with process_lock_cm(lock_name=lock_name, wait=wait):
                return fn(*args, **kwargs)
        return _wrapped
    return process_lock_wrap


def waiting_task_decorator(lock_name: LOCK_FN_TYPE = None, *cargs, **copts):
    def _wrapped(task_fn: FunctionType) -> PromiseProxy:
        @celery_app.task(bind=True, *cargs, **copts)
        @wraps(task_fn)
        @process_lock_decorator(lock_name=lock_name, wait=True)
        def _task_fn_wrap(self, *args, **kwargs):
            return task_fn(*args, **kwargs)
        return _task_fn_wrap
    return _wrapped
