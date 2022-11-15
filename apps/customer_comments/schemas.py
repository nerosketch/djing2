from datetime import date

from djing2.lib.fastapi.types import OrmConf
from pydantic import BaseModel


class CustomerCommentModelBaseSchema(BaseModel):
    customer_id: int
    text: str


class CustomerCommentModelSchema(CustomerCommentModelBaseSchema):
    id: int
    author_id: int
    date_create: date
    author_name: str
    author_avatar: str
    can_remove: bool

    Config = OrmConf
