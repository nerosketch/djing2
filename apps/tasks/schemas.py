from typing import Optional
from datetime import date, datetime

from django.db.models.fields.files import FieldFile
from profiles.models import UserProfile
from pydantic import BaseModel, Field, validator
from django.utils.translation import gettext as _
from djing2.lib.fastapi.types import OrmConf
from tasks.models import TaskPriorities, delta_add_days, TaskStates


class RecipientsFieldMixin(BaseModel):
    recipients: list[int] = Field([], title=_("Recipients"))

    @validator('recipients', pre=True, always=True)
    def get_recipients(cls, recipients: list[UserProfile]):
        # TODO: Annotate recipients with ArrayAgg from postgres
        if not recipients:
            return []
        if isinstance(recipients, (list, tuple)):
            r = (i for i in recipients if isinstance(i, (UserProfile, int)))
            return [i.pk if isinstance(i, UserProfile) else i for i in r]
        r = [r.pk for r in recipients.all()]
        return r


class TaskBaseSchema(RecipientsFieldMixin):
    descr: Optional[str] = Field(None, title=_("Description"), max_length=128)
    priority: TaskPriorities = TaskPriorities.TASK_PRIORITY_LOW
    out_date: Optional[date] = Field(default_factory=delta_add_days, title=_("Reality"))
    task_mode_id: int = Field(title=_("The nature of the damage"))
    customer_id: int = Field(title=_("Customer"))


class TaskUpdateSchema(TaskBaseSchema):
    out_date: Optional[date] = None
    task_mode_id: Optional[int] = Field(None, title=_("The nature of the damage"))
    customer_id: Optional[int] = Field(None, title=_("Customer"))
    task_state: TaskStates


class TaskModelSchema(TaskBaseSchema):
    id: Optional[int] = None
    time_of_create: datetime = Field(title=_("Date of create"))
    author_id: Optional[int] = None
    author_full_name: str
    author_uname: str
    priority_name: str
    time_diff: str
    customer_address: str
    customer_full_name: str
    customer_uname: str
    customer_group: int
    comment_count: int = 0
    task_state: int
    state_str: str
    task_mode_id: Optional[int] = Field(None, title=_("The nature of the damage"))
    mode_str: str
    is_expired: bool
    doc_count: int = 0

    Config = OrmConf


class UserTaskBaseSchema(BaseModel):
    time_of_create: datetime = Field(title=_("Date of create"))
    state_str: str
    mode_str: str
    out_date: Optional[date] = Field(
        default_factory=delta_add_days,
        title=_("Reality")
    )


class ExtraCommentBaseSchema(BaseModel):
    text: str = Field(title=_("Text of comment"))
    task_id: int = Field(title=_("Task"))


class ExtraCommentModelSchema(ExtraCommentBaseSchema):
    id: Optional[int] = None
    date_create: datetime = Field(title=_("Time of create"))
    author_id: int = Field(0, title=_("Author"))
    author_name: str
    author_avatar: str
    can_remove: bool = False

    Config = OrmConf


class TaskStateChangeLogModelSchema(BaseModel):
    id: Optional[int] = None
    when: Optional[datetime] = None
    who_id: Optional[int] = None
    who_name: str
    human_representation: Optional[str] = None

    Config = OrmConf


class TaskDocumentAttachmentModelSchema(BaseModel):
    id: int
    title: str
    doc_file: str
    task_id: int
    create_time: datetime
    author_id: int

    Config = OrmConf

    @validator('doc_file', pre=True)
    def validate_doc_file(cls, v):
        if isinstance(v, FieldFile):
            return v.url
        return v


class TaskFinishDocumentBaseSchema(RecipientsFieldMixin):
    code: str = Field(max_length=64, title=_('Document code'))
    act_num: Optional[str] = Field(None, max_length=64, title=_('Act num'))
    task_id: int = Field(title=_("Task"))
    create_time: datetime = Field(title=_("Time of create"))
    finish_time: datetime = Field(title=_('Finish time'))
    cost: float = Field(title=_('Cost'))
    task_mode_id: Optional[int] = Field(None, title=_('Mode'))


class TaskFinishDocumentModelSchema(TaskFinishDocumentBaseSchema):
    id: int
    author_id: int = Field(title=_("Author"))
    recipients: list[int] = Field([], title=_("Recipients"))

    Config = OrmConf


class TaskModeModelBaseSchema(BaseModel):
    title: str = Field(title=_('Title'), max_length=64)


class TaskModeModelModelSchema(TaskModeModelBaseSchema):
    id: int

    Config = OrmConf


class StatePercentResponseSchema(BaseModel):
    num: int
    name: str
    count: int
    percent: float


class TaskModeReportAnnotationItem(BaseModel):
    mode: str
    task_count: int


class TaskModeReportResponse(BaseModel):
    annotation: list[TaskModeReportAnnotationItem]
