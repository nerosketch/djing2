import os
from typing import Optional
from datetime import datetime, date, timedelta
from decimal import Decimal

from django.utils.translation import gettext as _
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


class DetailedCustomerServiceModelSchema(CustomerServiceModelSchema):
    service: ServiceModelSchema


class PickServiceRequestSchema(BaseModel):
    service_id: int
    deadline: Optional[datetime] = None


class MakePaymentSHotRequestSchema(BaseModel):
    shot_id: int


class PeriodicPayForIdRequestSchema(BaseModel):
    periodic_pay_id: int
    next_pay: datetime


class ServiceUsersResponseSchema(BaseModel):
    id: int
    group_id: int
    username: str
    fio: str


class TypicalResponse(BaseModel):
    text: str
    status: bool


class AddBalanceRequestSchema(BaseModel):
    cost: float
    comment: Optional[str] = Field(None, max_length=128)

    @validator('cost')
    def validate_cost(cls, v: float):
        if v == 0.0:
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

    @validator('number')
    def validate_number(cls, v: str):
        if not v.isdigit():
            raise ValueError('number must be digital')

    @validator('date_of_acceptance')
    def validate_date_of_acceptance(cls, value: Optional[datetime]):
        now = datetime.now().date()
        old_date = datetime.now() - timedelta(days=365 * 100)
        if value >= now:
            raise ValueError(_("You can't specify the future"))
        elif value <= old_date.date():
            raise ValueError(_("Too old date. Must be newer than %s") % old_date.strftime('%Y-%m-%d %H:%M:%S'))
        return value


class PassportInfoModelSchema(PassportInfoBaseSchema):
    id: int
    registration_address_title: str

    Config = OrmConf


class CustomerServiceTypeReportResponseSchema(BaseModel):
    all_count: int = Field(title='All services count')
    admin_count: int = Field(title='Admin services count')
    zero_cost_count: int = Field(title='Zero cost services count')
    calc_type_counts: int = Field(title='Calculation types count')


class ActivityReportResponseSchema(BaseModel):
    all_count: int = Field(title='All services count')
    enabled_count: int = Field(title='Enabled services count')
    with_services_count: int
    active_count: int = Field(title='Active services count')
    commercial_customers: int


class GetAfkResponseSchema(BaseModel):
    timediff: str
    last_date: datetime
    customer_id: int
    customer_uname: str
    customer_fio: str
