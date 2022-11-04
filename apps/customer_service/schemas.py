from typing import Optional
from datetime import datetime
from pydantic import validator, BaseModel, Field
from djing2.lib.fastapi.types import OrmConf
from services.schemas import ServiceModelSchema


class CustomerServiceBaseSchema(BaseModel):
    deadline: Optional[datetime] = None


class CustomerServiceModelSchema(CustomerServiceBaseSchema):
    id: int
    service_id: int
    start_time: Optional[datetime] = None

    Config = OrmConf


class DetailedCustomerServiceModelSchema(CustomerServiceModelSchema):
    service: ServiceModelSchema


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
