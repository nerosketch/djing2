from datetime import datetime
from typing import Optional

from django.db.models.fields.files import FieldFile
from django.utils.translation import gettext as _
from djing2.lib.fastapi.types import OrmConf
from pydantic import BaseModel, Field, validator


class CustomerContractBaseSchema(BaseModel):
    customer_id: int
    start_service_time: datetime
    contract_number: str
    end_service_time: Optional[datetime] = None
    title: Optional[str] = Field(_('Contract default title'))
    note: Optional[str] = None
    extended_data: Optional[dict] = None


class CustomerContractSchema(CustomerContractBaseSchema):
    id: Optional[int] = None
    is_active: bool = False
    contract_number: str = ''
    customer_id: Optional[int] = None
    start_service_time: Optional[datetime] = None

    Config = OrmConf


class CustomerContractAttachmentBaseSchema(BaseModel):
    contract_id: int
    author_id: Optional[int] = None
    title: str
    doc_file: str

    @validator('doc_file', pre=True)
    def validate_doc_file(cls, v):
        if isinstance(v, FieldFile):
            return v.url
        return v


class CustomerContractAttachmentSchema(CustomerContractAttachmentBaseSchema):
    id: int
    create_time: datetime

    Config = OrmConf
