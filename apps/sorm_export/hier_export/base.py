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
    def _wrapped(event_time=None, *args, **kwargs):
        if event_time is None:
            event_time = datetime.now()
        elif isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time)

        serializer_class, gen_fn, qs, fname = fn(event_time=event_time, *args, **kwargs)

        def _val_fn(dat):
            ser = serializer_class(data=dat)
            ser.is_valid(raise_exception=True)
            return ser.data

        res_data = map(gen_fn, qs.iterator())
        res_data = (_val_fn(r) for r in res_data if r)

        return res_data, fname
    return _wrapped
