from typing import Optional
from datetime import date, datetime

from pydantic import BaseModel, Field
from django.utils.translation import gettext_lazy as _
from djing2.lib.fastapi.types import OrmConf
from tasks.models import TaskPriorities, delta_add_days


class TaskBaseSchema(BaseModel):
    descr: Optional[str] = Field(None, title=_("Description"), max_length=128)
    recipients: list[int] = Field(title=_("Recipients"))
    priority: TaskPriorities
    out_date: Optional[date] = Field(None, default_factory=delta_add_days, title=_("Reality"))
    task_mode_id: int = Field(title=_("The nature of the damage"))
    customer_id: int = Field(title=_("Customer"))


class TaskModelSchema(TaskBaseSchema):
    id: int
    author_id: Optional[int]
    time_of_create: datetime = Field(title=_("Date of create"))
    author_full_name: str
    author_uname: str
    priority_name: str
    time_diff: str
    customer_address: str
    customer_full_name: str
    customer_uname: str
    customer_group: int
    comment_count: int
    recipients: list[int]
    state_str: str
    mode_str: str
    is_expired: bool
    doc_count: int

    Config = OrmConf
