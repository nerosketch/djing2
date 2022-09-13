from datetime import datetime
from typing import Optional

from django.utils.translation import gettext as _
from djing2.lib.fastapi.types import OrmConf
from pydantic import BaseModel, Field


class CustomerContractBaseSchema(BaseModel):
    customer_id: int
    start_service_time: datetime
    contract_number: str
    end_service_time: Optional[datetime] = None
    title: Optional[str] = Field(_('Contract default title'))
    note: Optional[str] = None
    extended_data: Optional[dict] = None


class CustomerContractSchema(CustomerContractBaseSchema):
    id: int
    is_active: bool = False

    Config = OrmConf


class CustomerContractAttachmentBaseSchema(BaseModel):
    contract_id: int
    author_id: Optional[int] = None
    title: str
    doc_file: str


class CustomerContractAttachmentSchema(CustomerContractAttachmentBaseSchema):
    id: int
    create_time: datetime

    Config = OrmConf
