from datetime import datetime
from functools import wraps


_fname_date_format = '%d%m%Y%H%M%S'


def format_fname(fname_timestamp=None) -> str:
    if fname_timestamp is None:
        fname_timestamp = datetime.now()
    return fname_timestamp.strftime(_fname_date_format)


def exp_dec(fn):
    @wraps(fn)
    def _wrapped(event_time=None, *args, **kwargs):
        if event_time is not None and isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time)
        ser, fname = fn(event_time=event_time, *args, **kwargs)
        ser.is_valid(raise_exception=True)
        return ser.data, fname
    return _wrapped
