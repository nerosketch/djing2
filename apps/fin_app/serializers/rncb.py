from collections import OrderedDict
from rest_framework import serializers
from rest_framework import status
from django.core.validators import integer_validator
from djing2.lib import IntEnumEx
from djing2.lib.mixins import BaseCustomModelSerializer
from fin_app.models.rncb import PayRNCBGateway, RNCBPayLog


date_format = '%Y%m%d%H%M%S'


class RNCBPaymentErrorEnum(IntEnumEx):
    OK = 0
    CUSTOMER_NOT_FOUND = 1
    SPECIFIED_FUTURE = 4
    DUPLICATE_TRANSACTION = 10

    # Custom error nums
    UNKNOWN_CODE = 100


class RNCBProtocolErrorExeption(serializers.ValidationError):
    status_code = status.HTTP_200_OK
    default_detail = 'Payment protocol error.'
    default_error: RNCBPaymentErrorEnum = RNCBPaymentErrorEnum.UNKNOWN_CODE

    def __init__(self, detail=None, error=None, code=None):
        super().__init__(detail=detail, code=code)
        self.error = error or self.default_error


class PayRNCBGatewayModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = PayRNCBGateway


class RNCBPayLogModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = RNCBPayLog


class RNCBPaymentCheckSerializer(serializers.Serializer):
    account = serializers.CharField(max_length=64, validators=[integer_validator])


class RNCBPaymentCheckResponseSerializer(serializers.Serializer):
    fio = serializers.CharField()

    # Negative from customer balance.
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False, required=False)

    error = serializers.ChoiceField(
        choices=RNCBPaymentErrorEnum.choices,
        default=RNCBPaymentErrorEnum.OK,
    )

    comments = serializers.CharField(required=False)
    #  inn = serializers.IntegerField(min_value=1000000000, max_value=999999999999)


class RNCBPaymentPaySerializer(serializers.Serializer):
    payment_id = serializers.IntegerField(min_value=1)
    account = serializers.CharField(max_length=64, validators=[integer_validator])
    summa = serializers.IntegerField(min_value=0, max_value=50000)
    exec_date = serializers.DateTimeField(
        format=date_format
    )
    #  inn = serializers.IntegerField(min_value=1000000000, max_value=999999999999)


class RNCBPaymentPayResponseSerializer(serializers.Serializer):
    out_payment_id = serializers.IntegerField() # Уникальный идентификатор Перевода в ИС Клиента
    error = serializers.ChoiceField(
        choices=RNCBPaymentErrorEnum.choices,
        default=RNCBPaymentErrorEnum.OK.value,
    )
    comments = serializers.CharField(required=False)


class RNCBPaymentTransactionCheckSerializer(serializers.Serializer):
    dateftom = serializers.DateTimeField(format=date_format)
    dateto = serializers.DateTimeField(format=date_format)

    def validate(self, data: OrderedDict):
        date_from = data['datefrom']
        date_to = data['dateto']
        if date_from > date_to:
            raise RNCBProtocolErrorExeption("DATEFROM Can't be more then DATETO")
        elif date_from == date_to:
            raise RNCBProtocolErrorExeption('Empty time interval')
        return data


class RNCBPaymentTransactionCheckResponseRowSerializer(serializers.Serializer):
    payment_row = serializers.CharField()


class RNCBPaymentTransactionCheckResponseSerializer(serializers.Serializer):
    full_summa = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False, required=False)
    number_of_payments = serializers.IntegerField()
    error = serializers.ChoiceField(
        choices=RNCBPaymentErrorEnum.choices,
        default=RNCBPaymentErrorEnum.OK.value,
    )
    payments = RNCBPaymentTransactionCheckResponseRowSerializer(many=True)

