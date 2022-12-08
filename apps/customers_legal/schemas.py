import re
from datetime import datetime
from typing import Optional

from customers_legal.models import CustomerLegalIntegerChoices
from django.conf import settings
from djing2.lib.fastapi.types import OrmConf
from profiles.schemas import BaseAccountSchema
from pydantic import BaseModel, Field, validator


class CustomerLegalBaseSchema(BaseAccountSchema):
    group_id: Optional[int] = None
    address_id: Optional[int] = None
    post_index: Optional[str] = Field(None, max_length=6)
    delivery_address_id: Optional[int] = None
    delivery_address_post_index: Optional[str] = Field(None, max_length=6)
    post_post_index: Optional[str] = Field(None, max_length=6)
    post_address_id: Optional[int] = None
    legal_type: CustomerLegalIntegerChoices = CustomerLegalIntegerChoices.NOT_CHOSEN
    tax_number: str
    state_level_reg_number: str
    actual_start_time: datetime
    actual_end_time: Optional[datetime] = None
    title: str
    description: Optional[str] = None


class CustomerLegalSchema(CustomerLegalBaseSchema):
    id: int
    balance: float
    fio: Optional[str] = None
    state_level_reg_number: Optional[str] = None
    actual_start_time: Optional[datetime] = None

    @validator('fio')
    def validate_fio(cls, full_fio: Optional[str]) -> str:
        # TODO: validate it
        return full_fio

    Config = OrmConf


class LegalCustomerBankBaseSchema(BaseModel):
    legal_customer_id: int
    title: str
    bank_code: str
    correspondent_account: str
    settlement_account: str


class LegalCustomerBankSchema(LegalCustomerBankBaseSchema):
    id: int
    number: Optional[str] = None

    Config = OrmConf


_tel_reg = re.compile(getattr(settings, "TELEPHONE_REGEXP", r"^(\+[7893]\d{10,11})?$"))


class CustomerLegalTelephoneBaseSchema(BaseModel):
    legal_customer_id: int
    telephone: str
    owner_name: str

    @validator('telephone')
    def check_telephone(cls, v: str):
        _reg = _tel_reg.search(v)
        if not _reg:
            raise ValueError('Bad phone number, check it')


class CustomerLegalTelephoneSchema(CustomerLegalTelephoneBaseSchema):
    id: int
    create_time: str
    create_time: datetime
    last_change_time: Optional[datetime] = None

    Config = OrmConf
