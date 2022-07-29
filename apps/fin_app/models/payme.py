from typing import Dict
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException
from djing2.lib import IntEnumEx
from .base_payment_model import (
    BasePaymentModel,
    BasePaymentLogModel,
    add_payment_type
)


PAYME_DB_TYPE_ID = 4


class PaymeErrorsEnum(IntEnumEx):
    METHOD_IS_NO_POST = -32300
    JSON_PARSE_ERROR = -32700
    RPC_PARSE_ERROR = -32600
    RPC_METHOD_NOT_FOUND = -32601
    PERMISSION_DENIED = -32504
    SERVER_ERROR = -32400

    CUSTOMER_DOES_NOT_EXISTS = -31050


class PaymeBaseRPCException(APIException):
    code: PaymeErrorsEnum = PaymeErrorsEnum.SERVER_ERROR
    msg = {
        'ru': 'Не известная ошибка',
        'en': 'Unknown error',
    }

    def get_code(self) -> PaymeErrorsEnum:
        return self.code

    def get_msg(self) -> Dict[str, str]:
        return self.msg


class PaymeRpcMethodError(PaymeBaseRPCException):
    code = PaymeErrorsEnum.RPC_METHOD_NOT_FOUND
    msg = {
        'ru': '',
        'en': ''
    }


class PaymeRPCMethodNames(models.TextChoices):
    CHECK_PERFORM_TRANSACTION = 'CheckPerformTransaction'
    CREATE_TRANSACTION = 'CreateTransaction'
    PERFORM_TRANSACTION = 'PerformTransaction'
    CANCEL_TRANSACTION = 'CancelTransaction'
    CHECK_TRANSACTION = 'CheckTransaction'
    GET_STATEMENT = 'GetStatement'


class PaymePaymentGatewayModelManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(payment_type=PAYME_DB_TYPE_ID)


class PaymePaymentGatewayModel(BasePaymentModel):
    pay_system_title = "Payme"

    objects = PaymePaymentGatewayModelManager()

    def save(self, *args, **kwargs):
        self.payment_type = PAYME_DB_TYPE_ID
        return super().save(*args, **kwargs)

    class Meta:
        db_table = 'payme_payment_gateway'


class TransactionStatesEnum(IntEnumEx):
    START = 1
    CANCELLED = 2
    PERFORMED = 3


class PaymePaymentLogModel(BasePaymentLogModel):
    transaction_state = models.IntegerField(
        choices=TransactionStatesEnum.choices,
        default=TransactionStatesEnum.START
    )

    def __str__(self):
        return f'PaymeLog{self.pk}: {self.get_transaction_state_display()}'


add_payment_type(PAYME_DB_TYPE_ID, PaymePaymentGatewayModel)
