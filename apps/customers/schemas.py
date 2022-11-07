import os
from typing import Optional
from datetime import datetime, date
from decimal import Decimal

from django.utils.translation import gettext as _

from djing2.lib import get_past_time_days
from djing2.lib.fastapi.types import OrmConf
from djing2.lib.validators import tel_regexp_str
from pydantic import validator, BaseModel, Field

from profiles.schemas import BaseAccountSchema

from . import models


def update_passw(acc, raw_password):
    if raw_password:
        updated_count = models.CustomerRawPassword.objects.filter(
            customer=acc
        ).update(
            passw_text=raw_password
        )
        if updated_count == 0:
            models.CustomerRawPassword.objects.create(
                customer=acc,
                passw_text=raw_password
            )


class CustomerSchema(BaseAccountSchema):
    group_id: Optional[int] = None
    fio: Optional[str] = None
    address_id: Optional[int] = None
    description: Optional[str] = None
    device_id: Optional[int] = None
    dev_port_id: Optional[int] = None
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
    marker_icons: list[str] = Field([], title='Marker icons')
    current_service_id: Optional[int] = None

    @validator('balance')
    def check_balance(cls, v: float):
        return round(v, 2)

    Config = OrmConf


class CustomerLogModelSchema(BaseModel):
    id: Optional[int] = None
    customer_id: Optional[int] = None
    author_id: Optional[int] = None
    comment: str
    date: datetime
    author_name: Optional[str] = None
    cost: float = 0.0
    from_balance: float = 0.0
    to_balance: float = 0.0

    @validator('cost')
    def validate_cost(cls, v: float):
        return round(v, 2)

    @validator('from_balance')
    def validate_from_balance(cls, v: float):
        return round(v, 2)

    @validator('to_balance')
    def validate_to_balance(cls, v: float):
        return round(v, 2)

    @validator('date')
    def validate_date(cls, v: datetime) -> str:
        return v.strftime('%Y-%m-%d %H:%M')

    Config = OrmConf


class InvoiceForPaymentBaseSchema(BaseModel):
    customer_id: int
    status: bool = False
    comment: str
    date_pay: Optional[datetime]
    cost: Decimal


class InvoiceForPaymentModelSchema(InvoiceForPaymentBaseSchema):
    id: int
    date_create: datetime
    author_id: int
    author_name: Optional[str] = None
    author_uname: Optional[str] = None

    Config = OrmConf


class CustomerRawPasswordBaseSchema(BaseModel):
    passw_text: str


class CustomerRawPasswordModelSchema(CustomerRawPasswordBaseSchema):
    id: int
    customer_id: int

    Config = OrmConf


class AdditionalTelephoneBaseSchema(BaseModel):
    telephone: str = Field(regex=tel_regexp_str)
    customer_id: int
    owner_name: str


class AdditionalTelephoneModelSchema(AdditionalTelephoneBaseSchema):
    id: int
    create_time: datetime

    Config = OrmConf


class AttachGroupServiceResponseSchema(BaseModel):
    service: int
    check: bool
    service_name: Optional[str] = None


class CustomerAttachmentModelSchema(BaseModel):
    id: int
    create_time: datetime
    title: str
    doc_file: str
    author_id: int
    author_name: Optional[str] = None
    customer_id: int
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
    telephone: str = Field(regex=tel_regexp_str)


class UserCustomerModelSchema(UserCustomerWritableModelSchema):
    id: int
    create_date: date
    last_update_time: Optional[datetime]
    full_name: str
    fio: str
    username: str
    telephone: Optional[str]
    birth_day: Optional[date] = None

    address_title: str
    balance: float
    last_connected_service_title: Optional[str]
    current_service_title: Optional[str]
    service_id: Optional[int]
    current_service_id: Optional[int] = None

    last_connected_service_id: Optional[int] = None

    Config = OrmConf

    @validator('balance')
    def check_balance(cls, v: float):
        return round(v, 2)


class UserBuyServiceSchema(BaseModel):
    service_id: int


class UserAutoRenewalServiceSchema(BaseModel):
    auto_renewal_service: bool


class ServiceUsersResponseSchema(BaseModel):
    id: int
    group_id: int
    username: str
    fio: str


class TypicalResponse(BaseModel):
    text: str
    status: bool


class AddBalanceRequestSchema(BaseModel):
    cost: Decimal = Field(max_digits=7, decimal_places=2)
    comment: Optional[str] = Field(None, max_length=128)

    @validator('cost')
    def validate_cost(cls, v: Decimal):
        if v.is_zero():
            raise ValueError('Passed invalid cost parameter')
        return v


class SetServiceGroupAccessoryRequestSchema(BaseModel):
    group_id: int
    services: list[int]


def _passport_distributor_default():
    return os.getenv(
        'CUSTOMERS_PASSPORT_DEFAULT_DISTRIBUTOR',
        'customers passport default distributor'
    )


class PassportInfoBaseSchema(BaseModel):
    series: str = Field(max_length=4, title=_("Passport serial"))
    number: str = Field(max_length=6, title=_("Passport number"))
    distributor: str = Field(
        _passport_distributor_default(),
        max_length=512,
        description=_("Distributor")
    )
    date_of_acceptance: Optional[date] = Field(None, description=_("Date of acceptance"))
    division_code: Optional[str] = Field(None, max_length=64, description=_("Division code"))
    # customer_id: Optional[int] = None
    registration_address_id: Optional[int]

    @validator('series')
    def validate_series(cls, v: str):
        if not v.isdigit():
            raise ValueError('series must be digital')
        return v

    @validator('number')
    def validate_number(cls, v: str):
        if not v.isdigit():
            raise ValueError('number must be digital')
        return v

    @validator('date_of_acceptance')
    def validate_date_of_acceptance(cls, date_of_acceptance: Optional[datetime]):
        now = datetime.now()
        now_date = now.date()
        hundred_years_ago = get_past_time_days(
            how_long_days=365 * 100,
            now=now
        )
        if date_of_acceptance >= now_date:
            raise ValueError(_("You can't specify the future"))
        elif date_of_acceptance <= hundred_years_ago.date():
            raise ValueError(_("Too old date. Must be newer than %s") % hundred_years_ago.strftime('%Y-%m-%d %H:%M:%S'))
        return date_of_acceptance


class PassportInfoModelSchema(PassportInfoBaseSchema):
    id: int
    series: Optional[str] = None
    number: Optional[str] = None
    distributor: Optional[str] = None
    registration_address_title: str

    @validator('series')
    def validate_series(cls, v: str):
        return v or ''

    @validator('number')
    def validate_number(cls, v: str):
        return v or ''

    Config = OrmConf


class GetAfkResponseSchema(BaseModel):
    timediff: str
    last_date: datetime
    customer_id: int
    customer_uname: str
    customer_fio: str
