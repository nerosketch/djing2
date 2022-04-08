from typing import Tuple, Any
from datetime import datetime
from functools import wraps

from djing2.lib.logger import logger
from rest_framework.exceptions import ValidationError


_fname_date_format = '%d%m%Y%H%M%S'


def format_fname(fname_timestamp=None) -> str:
    if fname_timestamp is None:
        fname_timestamp = datetime.now()
    return fname_timestamp.strftime(_fname_date_format)


def simple_export_decorator(fn):
    @wraps(fn)
    def _wrapped(event_time=None, *args, **kwargs):
        if event_time is None:
            event_time = datetime.now()
        elif isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time)
        ser, fname = fn(event_time=event_time, *args, **kwargs)
        ser.is_valid(raise_exception=True)
        return ser.data, fname
    return _wrapped


def iterable_export_decorator(fn):
    @wraps(fn)
    def _wrapped(event_time=None, *args, **kwargs) -> Tuple[Any, str]:
        if event_time is None:
            event_time = datetime.now()
        elif isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time)

        serializer_class, gen_fn, qs, fname = fn(event_time=event_time, *args, **kwargs)

        def _val_fn(dat):
            try:
                ser = serializer_class(data=dat)
                ser.is_valid(raise_exception=True)
                return ser.data
            except ValidationError as e:
                logger.error("%s | %s" % (e.detail, dat))

        res_data = map(gen_fn, qs)
        res_data = (_val_fn(r) for r in res_data if r)
        res_data = (r for r in res_data if r)

        return res_data, fname
    return _wrapped


def iterable_gen_export_decorator(fn):
    @wraps(fn)
    def _wrapped(event_time=None, *args, **kwargs) -> Tuple[Any, str]:
        if event_time is None:
            event_time = datetime.now()
        elif isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time)

        serializer_class, gen_fn, fname = fn(event_time=event_time, *args, **kwargs)

        def _val_fn(dat):
            try:
                ser = serializer_class(data=dat)
                ser.is_valid(raise_exception=True)
                return ser.data
            except ValidationError as e:
                logger.error("%s | %s" % (e.detail, dat))

        # res_data = map(gen_fn, qs.iterator())
        res_data = (_val_fn(r) for r in gen_fn() if r)
        res_data = (r for r in res_data if r)

        return res_data, fname
    return _wrapped

