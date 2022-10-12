import pytz
from enum import IntEnum
from collections.abc import Iterator
from datetime import timedelta, datetime
from hashlib import sha256
from typing import Any, Union, Optional, Mapping
from ipaddress import ip_address, ip_network

from django.conf import settings
from django.db.models.enums import ChoicesMeta
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from fastapi import HTTPException
from rest_framework.exceptions import APIException
from .process_lock import process_lock_decorator, ProcessLocked


def safe_float(fl: Any, default=0.0) -> float:
    if isinstance(fl, float):
        return fl
    try:
        return default if not fl else float(fl or 0)
    except (ValueError, OverflowError):
        return default


def safe_int(i: Any, default=0) -> int:
    if isinstance(i, int):
        return i
    try:
        return default if not i else int(i)
    except (ValueError, OverflowError):
        return default


# Exceptions
class LogicError(HTTPException):
    default_detail = _("Internal logic error")

    def __init__(self, detail=None, status_code: Optional[int] = None):
        super().__init__(
            detail=detail or self.default_detail,
            status_code=status_code
        )


class DuplicateEntry(APIException):
    """Raises when raised IntegrityError in db"""

    default_detail = _("Duplicate entry error")


# Предназначен для Django CHOICES чтоб можно было передавать
# классы вместо просто описания поля, классы передавать для
# того чтоб по значению кода из базы понять какой класс нужно
# взять для нужной функциональности. Например по коду в базе
# вам нужно определять как считать тариф абонента, что
# реализовано в возвращаемом классе.
class MyChoicesAdapter(Iterator):
    _chs = None

    # На вход принимает кортеж кортежей, вложенный из 2х элементов: кода и класса
    def __init__(self, choices):
        self._chs = iter(choices)

    def __next__(self):
        obj = next(self._chs)
        choice_code, choice_class = obj
        return choice_code, choice_class.description


# Russian localized timedelta
class RuTimedelta(timedelta):
    def __str__(self):
        if not str(self.days).isnumeric():
            raise TypeError("Date days is not numeric")
        last_digit = int(str(self.days)[-1:])
        if last_digit > 1:
            ru_days = "дней"
            if 5 > last_digit > 1:
                ru_days = "дня"
            elif last_digit == 1:
                ru_days = "день"
            # text_date = '%d %s %s' % (self.days, ru_days, text_date)
            text_date = "%d %s" % (last_digit, ru_days)
        else:
            text_date = super().__str__()
        return text_date


def bytes2human(bytes_len: Union[int, float], bsize=1024) -> str:
    notation = 0
    curr_len = bytes_len
    while curr_len > bsize:
        curr_len = curr_len / bsize
        notation += 1
    a = {0: "bytes", 1: "kb", 2: "mb", 3: "gb", 4: "tb", 5: "pb", 6: "eb"}
    return "{:.2f} {}".format(curr_len, a.get(notation, "X3"))


#
# Function for hash auth
#


def calc_hash(get_values: dict) -> str:
    api_auth_secret = getattr(settings, "API_AUTH_SECRET")
    get_list = [v for v in get_values.values() if v]
    get_list.sort()
    get_list.append(api_auth_secret)
    hashed = "_".join(get_list)

    if isinstance(hashed, str):
        result_data = hashed.encode("utf-8")
    else:
        result_data = bytes(hashed)
    return sha256(result_data).hexdigest()


def check_sign(get_values: dict, external_sign: str) -> bool:
    my_sign = calc_hash(get_values)
    return external_sign == my_sign


def check_subnet(headers_dict: Mapping[str, str]):
    """
    Check if user ip in allowed subnet.
    Return 403 denied otherwise.
    """
    ip = headers_dict.get("HTTP_X_REAL_IP", headers_dict.get('REMOTE_ADDR'))
    if ip is None:
        raise ValueError("Failed to get remote addr")
    ip = ip_address(ip)
    api_auth_subnet = getattr(settings, "API_AUTH_SUBNET")
    if isinstance(api_auth_subnet, (str, bytes)):
        if ip in ip_network(api_auth_subnet):
            return
    elif isinstance(api_auth_subnet, (list, tuple)):
        for subnet in api_auth_subnet:
            if ip in ip_network(subnet, strict=False):
                return
    raise ValueError("Bad Subnet")


# TODO: Replace it by netaddr.EUI
def macbin2str(bin_mac: bytes) -> str:
    if isinstance(bin_mac, (bytes, bytearray)):
        return ":".join("%.2x" % i for i in bin_mac) if bin_mac else None
    return ":".join("%.2x" % ord(i) for i in bin_mac) if bin_mac else None


def time2utctime(src_datetime) -> datetime:
    """Convert datetime from local tz to UTC"""
    tz = timezone.get_current_timezone()
    return tz.localize(src_datetime).astimezone(pytz.utc)


class IntEnumEx(IntEnum, metaclass=ChoicesMeta):
    @classmethod
    def in_range(cls, value: int):
        return value in cls._value2member_map_


__all__ = (
    'safe_float', 'safe_int', 'LogicError', 'DuplicateEntry',
    'MyChoicesAdapter', 'RuTimedelta', 'bytes2human', 'calc_hash',
    'check_sign', 'macbin2str', 'time2utctime', 'IntEnumEx',
    'process_lock_decorator', 'ProcessLocked', 'check_subnet'
)
