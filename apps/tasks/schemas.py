from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, Field
from django.utils.translation import gettext_lazy as _
from tasks.models import TaskPriorities, delta_add_days


class TaskBaseSchema(BaseModel):
    descr: Optional[str] = Field(None, title=_("Description"), max_length=128)
    recipients: list[int] = Field(title=_("Recipients"))
    priority: TaskPriorities
    out_date: Optional[date] = Field(None, default_factory=delta_add_days, title=_("Reality"))
    продолжить


class TaskModelSchema(TaskBaseSchema):
    id: int
    author_id: Optional[int]
    time_of_create: datetime = Field(title=_("Date of create"))
