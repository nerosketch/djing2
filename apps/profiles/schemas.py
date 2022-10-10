import re
from datetime import datetime, date
from typing import Optional
from string import digits

from pydantic import BaseModel, validator, Field
from django.utils.translation import gettext as _
from django.utils.crypto import get_random_string
from djing2.lib.validators import tel_regexp_str
from djing2.lib import safe_int
from profiles.models import BaseAccount, UserProfile, UserProfileLog, ProfileAuthLog, split_fio


def _is_chunk_ok(v: str, rgxp=re.compile(r"^[A-Za-zА-Яа-яЁё-]{1,50}$")):
    r = rgxp.search(v)
    return bool(r)


err_ex = ValueError(
    _('Credentials must be without spaces or any special symbols, only letters and "-"')
)


def generate_random_username():
    username = get_random_string(length=6, allowed_chars=digits)
    try:
        BaseAccount.objects.get(username=username)
        return generate_random_username()
    except BaseAccount.DoesNotExist:
        return str(safe_int(username))


def generate_random_password():
    return get_random_string(length=8, allowed_chars=digits)


class BaseAccountSchema(BaseModel):
    username: str = Field(default=generate_random_username)
    password: str = Field(default=generate_random_password)
    fio: str
    birth_day: Optional[date]
    is_active: bool = False
    # is_admin: bool = False
    telephone: Optional[str] = Field(None, regex=tel_regexp_str)

    @validator('fio')
    def validate_fio(cls, full_fio: str) -> str:
        res = split_fio(full_fio)
        if len(res) == 3:
            surname, name, last_name = res
            if surname is not None and not _is_chunk_ok(surname):
                raise err_ex
            if name is not None and not _is_chunk_ok(name):
                raise err_ex
            if last_name is not None and not _is_chunk_ok(last_name):
                raise err_ex

            return f"{surname} {name} {last_name or ''}"
        raise ValueError(_('3 words required: surname, name and last_name without spaces'))


class BaseAccountModelSchema(BaseAccountSchema):
    id: int
    create_date: date
    last_update_time: Optional[datetime]
    full_name: str
