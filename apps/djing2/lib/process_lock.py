import socket
from time import sleep
from types import FunctionType
from functools import wraps
from celery.utils.log import get_task_logger
from djing2 import celery_app
from celery.local import PromiseProxy

logger = get_task_logger(__name__)

LOCK_EXPIRE = 60 * 10  # Lock expires in 10 minutes


class ProcessLocked(OSError):
    """only one process for function"""


def process_lock(lock_name=None, wait=False):
    def process_lock_wrap(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            s = None
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                # Create an abstract socket, by prefixing it with null.
                if callable(lock_name):
                    really_lock_name = lock_name()
                else:
                    really_lock_name = str(lock_name)
                lock_fn_name = really_lock_name if really_lock_name is not None else fn.__name__
                if wait:
                    while True:
                        try:
                            logger.info('Try wait bind')
                            s.bind('\0djing2_lock_%s' % lock_fn_name)
                            logger.info('CONNECTED')
                            break
                        except OSError as err:
                            logger.debug('process %s busy, %s %s' % (lock_fn_name, fn, err))
                            sleep(0.2)
                else:
                    logger.info('Try one bind')
                    s.bind('\0djing2_lock_%s' % lock_fn_name)
                logger.info('exec func')
                return fn(*args, **kwargs)
            except OSError as err:
                logger.info('big os error')
                raise ProcessLocked from err
            finally:
                logger.info('finally')
                if s is not None:
                    logger.info('free s')
                    s.close()
        return wrapped
    return process_lock_wrap



def waiting_task_decorator(lock_name=None, *cargs, **copts):
    def _wrapped(task_fn: FunctionType) -> PromiseProxy:
        @celery_app.task(bind=True, *cargs, **copts)
        @wraps(task_fn)
        @process_lock(lock_name=lock_name, wait=True)
        def _task_fn_wrap(self, *args, **kwargs):
            return task_fn(*args, **kwargs)
        return _task_fn_wrap
    return _wrapped


import os
@waiting_task_decorator()
def port_fn():
    logger.debug('port_fn pre')
    if os.path.exists('/tmp/lock'):
        raise Exception
    with open('/tmp/lock', 'w') as f:
        f.write('ok')
    sleep(10)
    os.remove('/tmp/lock')
    logger.debug('port_fn post')
