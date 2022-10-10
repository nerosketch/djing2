from typing import Optional
from datetime import datetime, date
from decimal import Decimal

from djing2.lib.fastapi.types import OrmConf
from pydantic import validator, BaseModel, Field

from profiles.schemas import BaseAccountModelSchema, BaseAccountSchema


class CustomerSchema(BaseAccountSchema):
    balance: float
    current_service_id: Optional[int] = None
    group_id: Optional[int] = None
    address_id: Optional[int] = None
    description: Optional[str] = None
    device_id: Optional[int] = None
    dev_port: Optional[int] = None
    is_dynamic_ip: bool = False
    gateway_id: Optional[int] = None
    auto_renewal_service: bool = False
    last_connected_service_id: Optional[int] = None


class CustomerModelSchema(BaseAccountModelSchema):
    id: int
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

    @validator('balance')
    def check_balance(cls, v):
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
