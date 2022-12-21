from datetime import date
from decimal import Decimal
from typing import Optional

from django.utils.translation import gettext as _
from djing2.lib.fastapi.types import OrmConf
from djing2.lib.mixins import SitesBaseSchema
from pydantic import BaseModel, Field


class PaysReportParamsSchema(BaseModel):
    from_time: date
    to_time: date
    pay_gw_id: Optional[int] = None
    group_by: int = 0
    limit: int = Field(default=50, gt=0)


class PaysReportResponseSchema(BaseModel):
    summ: Decimal
    pay_count: int
    date_trunk: Optional[date] = None
    customer__fio: Optional[str] = None
    customer__username: Optional[str] = None


class BasePaymentBaseSchema(SitesBaseSchema):
    payment_type: Optional[int] = None
    title: Optional[str] = Field(default=None, title=_("Title"), max_length=64)
    slug: Optional[str] = Field(default=None, title=_("Slug"), max_length=32)


class BasePaymentModelSchema(BasePaymentBaseSchema):
    id: int
    pay_count: int = 0
    payment_type_text: str

    Config = OrmConf


class BasePaymentLogModelSchema(BaseModel):
    id: Optional[int] = None
    customer_id: Optional[int] = None
    pay_gw_id: Optional[int] = None
    date_add: Optional[date] = None
    amount: Decimal = Field(default=Decimal('0.0'), title=_("Cost"))

    Config = OrmConf
