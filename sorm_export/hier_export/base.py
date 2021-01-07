from datetime import datetime
from functools import wraps


_fname_date_format = '%d%m%Y%H%M%S'


def format_fname(fname_timestamp=None) -> str:
    if fname_timestamp is None:
        fname_timestamp = datetime.now()
    return fname_timestamp.strftime(_fname_date_format)


def simple_export_decorator(fn):
    @wraps(fn)
    def _wrapped(event_time=None, *args, **kwargs):
        if event_time is not None and isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time)
        ser, fname = fn(event_time=event_time, *args, **kwargs)
        ser.is_valid(raise_exception=True)
        return ser.data, fname
    return _wrapped


def iterable_export_decorator(fn):
    @wraps(fn)
    def _wrapped(event_time=None, *args, **kwargs):
        if event_time is not None and isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time)

        serializer_class, gen_fn, qs, fname = fn(event_time=event_time, *args, **kwargs)

        res_data = map(gen_fn, qs.iterator())
        ser = serializer_class(
            data=list(res_data), many=True
        )
        ser.is_valid(raise_exception=True)

        return ser.data, fname
    return _wrapped
