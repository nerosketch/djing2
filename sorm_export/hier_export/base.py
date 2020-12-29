from datetime import datetime
from functools import wraps


_fname_date_format = '%d%m%Y%H%M%S'


def format_fname(fname_timestamp=None) -> str:
    if fname_timestamp is None:
        fname_timestamp = datetime.now()
    return fname_timestamp.strftime(_fname_date_format)


def exp_dec(fn):
    @wraps(fn)
    def _wrapped(*args, **kwargs):
        ser, fname = fn(*args, **kwargs)
        ser.is_valid(raise_exception=True)
        # with open(fname, 'w') as f:
        #     f.write(ser.data)
        return ser.data, fname
    return _wrapped
