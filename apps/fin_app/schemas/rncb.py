from datetime import datetime
from decimal import Decimal
from typing import Optional

from djing2.exceptions import BaseProjectError
from djing2.lib import IntEnumEx
from django.utils.translation import gettext as _
from starlette import status
from pydantic import BaseModel, Field, validator, root_validator
from . import base


date_format = '%Y%m%d%H%M%S'


class RNCBPaymentErrorEnum(IntEnumEx):
    OK = 0
    CUSTOMER_NOT_FOUND = 1
    SPECIFIED_FUTURE = 4
    DUPLICATE_TRANSACTION = 10

    # Custom error nums
    UNKNOWN_CODE = 100


class RNCBProtocolErrorException(BaseProjectError):
    status_code = status.HTTP_200_OK
    default_detail = 'Payment protocol error.'
    default_error: RNCBPaymentErrorEnum = RNCBPaymentErrorEnum.UNKNOWN_CODE

    def __init__(self, detail=None, error=None, code=None):
        super().__init__(
            detail=detail,
            status_code=code
        )
        self.error = error or self.default_error


class PayRNCBGatewayModelSchema(base.BasePaymentModelSchema):
    pass


class RNCBPayLogModelSchema(base.BasePaymentLogModelSchema):
    pay_id: int
    acct_time: datetime = Field(title=_('Act time from payment system'))


class RNCBPaymentCheckSchema(BaseModel):
    account: str = Field(alias='Account', max_length=64)


class RNCBPaymentCheckResponseSchema(BaseModel):
    balance: Optional[Decimal] = Field(default=None, max_digits=12, decimal_places=2, alias='BALANCE')
    error: RNCBPaymentErrorEnum = Field(default=RNCBPaymentErrorEnum.OK, alias='ERROR')
    comments: Optional[str] = Field(default=None, alias='COMMENTS')


class RNCBPaymentPaySchema(BaseModel):
    payment_id: int = Field(alias='Payment_id', gt=0)
    account: str = Field(alias='Account', max_length=64)
    summa: Decimal = Field(ge=0, le=50000, max_digits=12, decimal_places=6, alias='Summa')
    exec_date: datetime = Field(alias='Exec_date')

    @validator('exec_date', pre=True)
    def validate_exec_date(cls, v):
        if isinstance(v, datetime):
            return v.strftime(fmt=date_format)
        return datetime.strptime(str(v), format=date_format)


class RNCBPaymentPayResponseSchema(BaseModel):
    out_payment_id: int = Field(alias='OUT_PAYMENT_ID')
    error: RNCBPaymentErrorEnum = Field(default=RNCBPaymentErrorEnum.OK, alias='ERROR')
    comments: Optional[str] = Field(default=None, alias='COMMENTS')


class RNCBPaymentTransactionCheckSchema(BaseModel):
    date_from: datetime = Field(alias='DateFrom')
    date_to: datetime = Field(alias='DateTo')

    @validator('date_from', pre=True)
    def validate_date_from(cls, v):
        if isinstance(v, datetime):
            return v.strftime(fmt=date_format)
        return datetime.strptime(str(v), format=date_format)

    @validator('date_to', pre=True)
    def validate_date_to(cls, v):
        if isinstance(v, datetime):
            return v.strftime(fmt=date_format)
        return datetime.strptime(str(v), format=date_format)

    @root_validator()
    def validate_dates(cls, data: dict):
        date_from = data['date_from']
        date_to = data['date_to']
        if date_from > date_to:
            raise RNCBProtocolErrorException("DATEFROM Can't be more then DATETO")
        elif date_from == date_to:
            raise RNCBProtocolErrorException('Empty time interval')
        return data


class RNCBPaymentTransactionCheckResponseSchema(BaseModel):
    full_summa: Optional[Decimal] = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
        alias='FULL_SUMMA'
    )
    number_of_payments: int = Field(alias='NUMBER_OF_PAYMENTS')
    error: RNCBPaymentErrorEnum = Field(default=RNCBPaymentErrorEnum.OK, alias='ERROR')
    payments: list = Field(alias='PAYMENTS')
