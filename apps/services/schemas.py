from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

from djing2.lib.fastapi.types import OrmConf
from services.custom_logic import ServiceChoiceEnum


class ServiceModelBaseSchema(BaseModel):
    title: str
    descr: Optional[str] = None
    speed_in: float = Field(ge=0.1)
    speed_out: float = Field(ge=0.1)
    speed_burst: float = 1.0
    cost: float = Field(ge=0.0)
    calc_type: ServiceChoiceEnum
    is_admin: bool = False


class ServiceModelSchema(ServiceModelBaseSchema):
    id: int
    create_time: Optional[datetime] = None
    usercount: Optional[int] = None
    planned_deadline: str
    calc_type_name: Optional[str] = None

    Config = OrmConf


class CustomerServiceBaseSchema(BaseModel):
    deadline: Optional[datetime] = None


class CustomerServiceModelSchema(CustomerServiceBaseSchema):
    id: int
    service_id: int
    start_time: Optional[datetime] = None

    Config = OrmConf


class DetailedCustomerServiceModelSchema(CustomerServiceModelSchema):
    service: ServiceModelSchema


class CustomerServiceTypeReportCalcType(BaseModel):
    calc_type_count: int
    service_descr: str


class CustomerServiceTypeReportResponseSchema(BaseModel):
    all_count: int = Field(title='All services count')
    admin_count: int = Field(title='Admin services count')
    zero_cost_count: int = Field(title='Zero cost services count')
    calc_type_counts: list[CustomerServiceTypeReportCalcType] = Field(title='Calculation types count')


class ActivityReportResponseSchema(BaseModel):
    all_count: int = Field(title='All services count')
    enabled_count: int = Field(title='Enabled services count')
    with_services_count: int
    active_count: int = Field(title='Active services count')
    commercial_customers: int


class PickServiceRequestSchema(BaseModel):
    service_id: int
    deadline: Optional[datetime] = None


class MakePaymentSHotRequestSchema(BaseModel):
    shot_id: int


class PeriodicPayForIdRequestSchema(BaseModel):
    periodic_pay_id: int
    next_pay: datetime


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


class CustomerServiceQueueBaseSchema(BaseModel):
    customer_id: int
    service_id: int


class CustomerServiceQueueModelSchema(CustomerServiceQueueBaseSchema):
    id: int
    number_queue: int = Field(gt=0, title='Number in queue')
    service_title: str

    Config = OrmConf
