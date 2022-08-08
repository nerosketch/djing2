from typing import Dict
from datetime import datetime, timedelta
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException
from djing2.lib import IntEnumEx
from .base_payment_model import (
    BasePaymentModel,
    BasePaymentLogModel,
    add_payment_type
)
from customers.models import Customer
from customers.tasks import customer_check_service_for_expiration


PAYME_DB_TYPE_ID = 4


class PaymeCancelReasonEnum(IntEnumEx):
    SOME_REMOTE_CUSTOMERS_INACTIVE = 1
    PROCESSING_OPERATION_ERROR = 2
    TRANSACTION_PROVIDE_ERROR = 3
    TRANSACTION_CANCELLED_BY_TIMEOUT = 4
    CASH_REFUND = 5
    UNKNOWN_ERROR = 10


class PaymeErrorsEnum(IntEnumEx):
    METHOD_IS_NO_POST = -32300
    JSON_PARSE_ERROR = -32700
    RPC_PARSE_ERROR = -32600
    RPC_METHOD_NOT_FOUND = -32601
    PERMISSION_DENIED = -32504
    SERVER_ERROR = -32400

    CUSTOMER_DOES_NOT_EXISTS = -31050
    VALIDATION_ERROR = -31051

    TRANSACTION_NOT_FOUND = -31003
    TRANSACTION_STATE_ERROR = -31008
    TRANSACTION_NOT_ALLOWED = -31007


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
        'ru': 'Метод не найден',
        'en': 'Method not found'
    }


class PaymeTransactionNotFound(PaymeBaseRPCException):
    code = PaymeErrorsEnum.TRANSACTION_NOT_FOUND
    msg = {
        'ru': 'Транзакция не найдена',
        'en': 'Transaction not found',
    }


class PaymeTransactionStateBad(PaymeBaseRPCException):
    code = PaymeErrorsEnum.TRANSACTION_STATE_ERROR
    msg = {
        'ru': 'Не правильный тип транзакции',
        'en': 'Bad transaction type',
    }


class PaymeTransactionTimeout(PaymeBaseRPCException):
    code = PaymeErrorsEnum.TRANSACTION_STATE_ERROR
    msg = {
        'ru': 'Транзакция устарела',
        'en': 'Transaction is timed out',
    }


class PaymeCustomerNotFound(PaymeBaseRPCException):
    code = PaymeErrorsEnum.CUSTOMER_DOES_NOT_EXISTS
    msg = {
        'ru': 'Абонент не найден',
        'en': 'Customer does not exists'
    }


class PaymeTransactionCancelNotAllowed(PaymeBaseRPCException):
    code = PaymeErrorsEnum.TRANSACTION_NOT_ALLOWED
    msg = {
        'ru': 'Запрещено отменять транзакцию',
        'en': 'Not allowed to cancel transaction'
    }


class PaymeValidationError(PaymeBaseRPCException):
    code = PaymeErrorsEnum.VALIDATION_ERROR
    msg = {
        'ru': 'Ошибка валидации',
        'en': 'Validation error'
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
        proxy = True
        #  db_table = 'payme_payment_gateway'


class TransactionStatesEnum(IntEnumEx):
    INITIAL = 0
    START = 1
    CANCELLED = -1
    PERFORMED = 2
    CANCELLED_AFTER_PERFORMED = -2


class PaymePaymentLogModel(BasePaymentLogModel):
    pass

    class Meta:
        proxy = True


add_payment_type(PAYME_DB_TYPE_ID, PaymePaymentGatewayModel)


class PaymeTransactionModelManager(models.Manager):
    def start_transaction(self, external_id: str, customer, external_time: datetime, amount: float):
        trans, created = self.get_or_create(
            external_id=external_id,
            defaults={
                'transaction_state': TransactionStatesEnum.START,
                'customer': customer,
                'external_time': external_time,
                'amount': amount
            }
        )
        if not created:
            if trans.transaction_state != TransactionStatesEnum.START:
                raise PaymeTransactionStateBad
            if trans.is_timed_out():
                trans.cancel()
                raise PaymeTransactionTimeout
        return trans

    def provide_payment(self, transaction_id: str, gw: PaymePaymentGatewayModel) -> dict:
        trans = self.filter(external_id=transaction_id).first()
        if trans is None:
            raise PaymeTransactionNotFound
        if trans.transaction_state == TransactionStatesEnum.CANCELLED:
            raise PaymeTransactionStateBad
        elif trans.transaction_state == TransactionStatesEnum.START:
            if trans.is_timed_out():
                trans.cancel()
                raise PaymeTransactionTimeout
            else:
                customer = trans.customer
                if not customer:
                    raise PaymeCustomerNotFound
                pay_amount = trans.amount
                with transaction.atomic():
                    customer.add_balance(
                        profile=None,
                        # TODO: change to Decimal
                        cost=float(pay_amount),
                        comment=f"{gw.title} {pay_amount:.2f}"
                    )
                    customer.save(update_fields=["balance"])
                    PaymePaymentLogModel.objects.create(
                        customer=customer,
                        pay_gw=gw,
                        amount=pay_amount,
                    )
                    trans.perform()
                customer_check_service_for_expiration(customer_id=customer.pk)
        return {'result': {
            'transaction': trans.pk,
            'perform_time': int(trans.date_add.timestamp() * 1000),
            'state': trans.transaction_state
        }}

    def cancel_transaction(self, transaction_id: str) -> dict:
        # trans = self.filter(external_id=transaction_id).first()
        # if trans is None:
        #     raise PaymeTransactionNotFound
        raise PaymeTransactionCancelNotAllowed

    def check_payment(self, transaction_id: str) -> dict:
        trans = self.filter(external_id=transaction_id).first()
        if trans is None:
            raise PaymeTransactionNotFound
        return {'result': {
            'create_time': trans.date_add.timestamp(),
            'perform_time': trans.perform_time.timestamp if trans.perform_time else 0,
            'cancel_time': trans.cancel_time.timestamp if trans.cancel_time else 0,
            'transaction': trans.pk,
            'state': trans.transaction_state,
            'reason': None
        }}


class PaymeTransactionModel(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_DEFAULT,
        blank=True, null=True, default=None
    )
    transaction_state = models.IntegerField(
        choices=TransactionStatesEnum.choices,
        default=TransactionStatesEnum.INITIAL
    )
    external_id = models.CharField(max_length=25, unique=True)
    external_time = models.DateTimeField()
    date_add = models.DateTimeField(auto_now_add=True)
    cancel_time = models.DateTimeField(null=True, blank=True, default=None)
    perform_time = models.DateTimeField(null=True, blank=True, default=None)
    amount = models.DecimalField(
        _("Cost"),
        default=0.0,
        max_digits=19,
        decimal_places=6
    )

    def is_timed_out(self) -> bool:
        transaction_deadline = self.date_add + timedelta(days=1)
        return datetime.now() >= transaction_deadline

    def cancel(self):
        self.transaction_state = TransactionStatesEnum.CANCELLED
        self.cancel_time = datetime.now()
        self.save(update_fields=['transaction_state'])

    def perform(self):
        self.transaction_state = TransactionStatesEnum.PERFORMED
        self.perform_time = datetime.now()
        self.save(update_fields=['transaction_state', 'perform_time'])

    objects = PaymeTransactionModelManager()

    def __str__(self):
        return self.external_id
