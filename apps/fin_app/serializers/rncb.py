from collections import OrderedDict
from rest_framework import serializers
from rest_framework import status
from django.core.validators import integer_validator
from djing2.lib import IntEnumEx
from djing2.lib.mixins import BaseCustomModelSerializer
from fin_app.models.rncb import RNCBPaymentGateway, RNCBPaymentLog


date_format = '%Y%m%d%H%M%S'


class RNCBPaymentErrorEnum(IntEnumEx):
    OK = 0
    CUSTOMER_NOT_FOUND = 1
    SPECIFIED_FUTURE = 4
    DUPLICATE_TRANSACTION = 10

    # Custom error nums
    UNKNOWN_CODE = 100


class RNCBProtocolErrorException(serializers.ValidationError):
    status_code = status.HTTP_200_OK
    default_detail = 'Payment protocol error.'
    default_error: RNCBPaymentErrorEnum = RNCBPaymentErrorEnum.UNKNOWN_CODE

    def __init__(self, detail=None, error=None, code=None):
        super().__init__(detail=detail, code=code)
        self.error = error or self.default_error


class PayRNCBGatewayModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = RNCBPaymentGateway


class RNCBPayLogModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = RNCBPaymentLog


class RNCBPaymentCheckSerializer(serializers.Serializer):
    Account = serializers.CharField(max_length=64, validators=[integer_validator])


class RNCBPaymentCheckResponseSerializer(serializers.Serializer):
    #  fio = serializers.CharField()

    # Negative from customer balance.
    BALANCE = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False, required=False)

    ERROR = serializers.ChoiceField(
        choices=RNCBPaymentErrorEnum.choices,
        default=RNCBPaymentErrorEnum.OK,
    )

    COMMENTS = serializers.CharField(required=False)
    #  inn = serializers.IntegerField(min_value=1000000000, max_value=999999999999)


class RNCBPaymentPaySerializer(serializers.Serializer):
    Payment_id = serializers.IntegerField(min_value=1)
    Account = serializers.CharField(max_length=64, validators=[integer_validator])
    Summa = serializers.DecimalField(min_value=0, max_value=50000, max_digits=12, decimal_places=6)
    Exec_date = serializers.DateTimeField(
        input_formats=[date_format], format=date_format
    )
    #  inn = serializers.IntegerField(min_value=1000000000, max_value=999999999999)


class RNCBPaymentPayResponseSerializer(serializers.Serializer):
    OUT_PAYMENT_ID = serializers.IntegerField() # Уникальный идентификатор Перевода в ИС Клиента
    ERROR = serializers.ChoiceField(
        choices=RNCBPaymentErrorEnum.choices,
        default=RNCBPaymentErrorEnum.OK.value,
    )
    COMMENTS = serializers.CharField(required=False)


class RNCBPaymentTransactionCheckSerializer(serializers.Serializer):
    DateFrom = serializers.DateTimeField(format=date_format, input_formats=[date_format])
    DateTo = serializers.DateTimeField(format=date_format, input_formats=[date_format])

    def validate(self, data: OrderedDict):
        date_from = data['DateFrom']
        date_to = data['DateTo']
        if date_from > date_to:
            raise RNCBProtocolErrorException("DATEFROM Can't be more then DATETO")
        elif date_from == date_to:
            raise RNCBProtocolErrorException('Empty time interval')
        return data


class RNCBPaymentTransactionCheckResponseSerializer(serializers.Serializer):
    FULL_SUMMA = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False, required=False)
    NUMBER_OF_PAYMENTS = serializers.IntegerField()
    ERROR = serializers.ChoiceField(
        choices=RNCBPaymentErrorEnum.choices,
        default=RNCBPaymentErrorEnum.OK.value,
    )
    PAYMENTS = serializers.ListField()

