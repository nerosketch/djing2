import re
from datetime import datetime, date
from typing import Optional
from string import digits

from asgiref.sync import sync_to_async
from djing2.lib.mixins import SitesBaseSchema
from pydantic import validator, Field
from django.utils.translation import gettext as _
from django.utils.crypto import get_random_string
from djing2.lib.validators import tel_regexp_str
from djing2.lib import safe_int
from profiles.models import BaseAccount, split_fio


def _is_chunk_ok(v: str, rgxp=re.compile(r"^[A-Za-zА-Яа-яЁё-]{1,50}$")):
    r = rgxp.search(v)
    return bool(r)


err_ex = ValueError(
    _('Credentials must be without spaces or any special symbols, only letters and "-"')
)


async def generate_random_username():
    username = get_random_string(length=6, allowed_chars=digits)
    if await sync_to_async(BaseAccount.objects.filter(username=username).exists)():
        return await generate_random_username()
    return str(safe_int(username))


def generate_random_password():
    return get_random_string(length=8, allowed_chars=digits)


class BaseAccountSchema(SitesBaseSchema):
    username: str = Field(default_factory=generate_random_username)
    password: str = Field(default_factory=generate_random_password)
    fio: str
    birth_day: Optional[date]
    is_active: bool = False
    # is_admin: bool = False
    telephone: Optional[str] = Field(None, regex=tel_regexp_str)

    @validator('fio')
    def validate_fio(cls, full_fio: str) -> str:
        r = split_fio(full_fio)
        if r.surname is not None and not _is_chunk_ok(r.surname):
            raise err_ex
        if r.name is not None and not _is_chunk_ok(r.name):
            raise err_ex
        if r.last_name is not None and not _is_chunk_ok(r.last_name):
            raise err_ex

        return str(r)


class BaseAccountModelSchema(BaseAccountSchema):
    id: int
    create_date: date
    last_update_time: Optional[datetime]
    full_name: str
