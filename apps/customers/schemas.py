from typing import Optional
from datetime import datetime, date
from decimal import Decimal

from djing2.lib.fastapi.types import OrmConf
from djing2.lib.validators import tel_regexp_str
from pydantic import validator, BaseModel, Field

from profiles.schemas import BaseAccountSchema
from services.schemas import ServiceModelSchema

from . import models


def update_passw(acc, raw_password):
    if raw_password:
        updated_count = models.CustomerRawPassword.objects.filter(customer=acc).update(passw_text=raw_password)
        if updated_count == 0:
            models.CustomerRawPassword.objects.create(customer=acc, passw_text=raw_password)


class CustomerSchema(BaseAccountSchema):
    group_id: Optional[int] = None
    address_id: Optional[int] = None
    description: Optional[str] = None
    device_id: Optional[int] = None
    dev_port: Optional[int] = None
    is_dynamic_ip: bool = False
    gateway_id: Optional[int] = None
    auto_renewal_service: bool = False
    last_connected_service_id: Optional[int] = None


class CustomerModelSchema(CustomerSchema):
    id: int
    create_date: date
    last_update_time: Optional[datetime]
    full_name: str

    group_title: Optional[str]
    address_title: str
    balance: float
    device_comment: Optional[str]
    last_connected_service_title: Optional[str]
    current_service_title: Optional[str]
    service_id: Optional[int]
    raw_password: Optional[str]
    lease_count: Optional[int] = None
    marker_icons: list[str] = []
    current_service_id: Optional[int] = None

    @validator('balance')
    def check_balance(cls, v: float):
        return round(v, 2)

    Config = OrmConf


class CustomerServiceBaseSchema(BaseModel):
    deadline: Optional[datetime] = None


class CustomerServiceModelSchema(CustomerServiceBaseSchema):
    id: int
    service_id: int
    start_time: Optional[datetime] = None

    Config = OrmConf


class CustomerLogModelSchema(BaseModel):
    id: int
    customer_id: int
    author_id: Optional[int] = None
    comment: str
    date: date
    author_name: Optional[str]
    cost: Decimal = Decimal(0.0)
    from_balance: Decimal = Decimal(0.0)
    to_balance: Decimal = Decimal(0.0)

    Config = OrmConf


class InvoiceForPaymentModelSchema(BaseModel):
    id: int
    customer_id: int
    status: bool = False
    comment: str
    date_create: datetime
    date_pay: Optional[datetime]
    author_id: int
    author_name: Optional[str] = None
    author_uname: Optional[str] = None
    cost: Decimal = 0.0

    Config = OrmConf


class CustomerRawPasswordModelSchema(BaseModel):
    id: int
    customer_id: int
    passw_text: str

    Config = OrmConf


class AdditionalTelephoneBaseSchema(BaseModel):
    telephone: str
    customer_id: int


class AdditionalTelephoneModelSchema(AdditionalTelephoneBaseSchema):
    id: int
    owner_name: str
    create_time: datetime

    Config = OrmConf


class PeriodicPayForIdBaseSchema(BaseModel):
    periodic_pay_id: int


class PeriodicPayForIdModelSchema(PeriodicPayForIdBaseSchema):
    id: int
    next_pay: datetime
    last_pay: Optional[datetime] = None
    service_name: Optional[str] = None
    service_calc_type: Optional[str] = None
    service_amount: Optional[float] = None

    Config = OrmConf


class AttachGroupServiceResponseSchema(BaseModel):
    service: int
    check: bool
    service_name: Optional[str] = None


class CustomerAttachmentBaseSchema(BaseModel):
    title: str
    doc_file: str
    customer_id: int


class CustomerAttachmentModelSchema(CustomerAttachmentBaseSchema):
    id: int
    create_time: datetime
    author_id: int
    author_name: Optional[str] = None
    customer_name: Optional[str] = None

    Config = OrmConf


class GroupsWithCustomersSchema(BaseModel):
    id: int
    title: str
    # sites: list[int]
    customer_count: int = 0

    Config = OrmConf


class TokenResponseSchema(BaseModel):
    token: Optional[str]


class TokenRequestSchema(BaseModel):
    telephone: str = Field(regex=tel_regexp_str)


class UserCustomerWritableModelSchema(BaseModel):
    address_id: Optional[int] = None
    auto_renewal_service: bool = False


class UserCustomerModelSchema(UserCustomerWritableModelSchema):
    id: int
    create_date: date
    last_update_time: Optional[datetime]
    full_name: str

    address_title: str
    balance: float
    last_connected_service_title: Optional[str]
    current_service_title: Optional[str]
    service_id: Optional[int]
    current_service_id: Optional[int] = None

    last_connected_service_id: Optional[int] = None

    Config = OrmConf


class UserBuyServiceSchema(BaseModel):
    service_id: int


class UserAutoRenewalServiceSchema(BaseModel):
    auto_renewal_service: bool


class DetailedCustomerServiceModelSchema(BaseModel):
    service: ServiceModelSchema

    Config = OrmConf


class PickServiceRequestSchema(BaseModel):
    service_id: int
    deadline: Optional[datetime] = None

class MakePaymentSHotRequestSchema(BaseModel):
    shot_id: int
