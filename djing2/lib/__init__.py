import socket
from functools import wraps
from hashlib import sha256
from datetime import timedelta
from collections import Iterator


def safe_float(fl):
    try:
        return 0.0 if not fl else float(fl)
    except (ValueError, OverflowError):
        return 0.0


def safe_int(i):
    try:
        return 0 if not i else int(i)
    except (ValueError, OverflowError):
        return 0


#
# Exceptions
#

class LogicError(Exception):
    pass


class DuplicateEntry(Exception):
    """Raises when raised IntegrityError in db"""


# Предназначен для Django CHOICES чтоб можно было передавать классы вместо просто описания поля,
# классы передавать для того чтоб по значению кода из базы понять какой класс нужно взять для нужной функциональности.
# Например по коду в базе вам нужно определять как считать тариф абонента, что реализовано в возвращаемом классе.
class MyChoicesAdapter(Iterator):
    _chs = None

    # На вход принимает кортеж кортежей, вложенный из 2х элементов: кода и класса
    def __init__(self, choices):
        self._chs = iter(choices)

    def __next__(self):
        obj = next(self._chs)
        choice_code, choice_class = obj
        return choice_code, choice_class.get_description()


# Russian localized timedelta
class RuTimedelta(timedelta):

    def __str__(self):
        if self.days > 1:
            ru_days = 'дней'
            if 5 > self.days > 1:
                ru_days = 'дня'
            elif self.days == 1:
                ru_days = 'день'
            # text_date = '%d %s %s' % (self.days, ru_days, text_date)
            text_date = '%d %s' % (self.days, ru_days)
        else:
            text_date = super().__str__()
        return text_date


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


#
# Function for hash auth
#

def calc_hash(data):
    if type(data) is str:
        result_data = data.encode('utf-8')
    else:
        result_data = bytes(data)
    return sha256(result_data).hexdigest()


def check_sign(get_list, sign):
    hashed = '_'.join(get_list)
    my_sign = calc_hash(hashed)
    return sign == my_sign


class ProcessLocked(OSError):
    """only one process for function"""


def process_lock(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        s = None
        try:
            s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            # Create an abstract socket, by prefixing it with null.
            s.bind('\0postconnect_djing2_lock_func_%s' % fn.__name__)
            return fn(*args, **kwargs)
        except socket.error:
            raise ProcessLocked
        finally:
            if s is not None:
                s.close()
    return wrapped
