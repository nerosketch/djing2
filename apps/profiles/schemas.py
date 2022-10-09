import re
from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, validator
from django.utils.translation import gettext as _
from profiles.models import split_fio


def _is_chunk_ok(v: str, rgxp=re.compile(r"^[A-Za-zА-Яа-яЁё-]{1,50}$")):
    r = rgxp.search(v)
    return bool(r)


err_ex = ValueError(
    _('Credentials must be without spaces or any special symbols, only letters and "-"')
)


class BaseAccountSchema(BaseModel):
    username: str
    fio: str
    birth_day: Optional[date]
    last_update_time: Optional[datetime]
    is_active: bool = False
    # is_admin: bool = False
    telephone: Optional[str]

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
    full_name: str
