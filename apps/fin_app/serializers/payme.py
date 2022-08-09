from datetime import datetime
from collections import OrderedDict
from django.utils.translation import gettext_lazy as _
from django.utils.regex_helper import _lazy_re_compile
from django.core.validators import integer_validator, RegexValidator
from rest_framework import serializers
from djing2.lib.mixins import BaseCustomModelSerializer
from djing2.serializers import TimestampField
from fin_app.models.payme import (
    PaymeCancelReasonEnum, PaymeTransactionModel,
    PaymeValidationError, PaymePaymentLogModel,
    PaymePaymentGatewayModel
)


class MilisecTimestampField(TimestampField):
    def to_internal_value(self, value: float) -> datetime:
        if isinstance(value, (float, int)):
            value = float(value) / 1000
        return super().to_internal_value(value)

    def to_representation(self, value):
        r = super().to_representation(value)
        return int(r * 1000)


def _base_request_wrapper(cls):
    class _PaymeBaseRequestSerializer(serializers.Serializer):
        method = serializers.CharField(label='Method', max_length=64)
        #  id = serializers.IntegerField(label='ID')
        params = cls()

    return _PaymeBaseRequestSerializer


class TransactionAccountRequestSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=64, validators=[integer_validator])


@_base_request_wrapper
class PaymeCheckPerformTransactionRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        label='Amount',
        required=True,
        max_digits=12,
        decimal_places=4
    )
    account = TransactionAccountRequestSerializer()


payment_id_validator = RegexValidator(
    _lazy_re_compile(r'^[0-9a-fA-F]{1,25}$'),
    message=_('Enter a valid ID value.'),
    code='invalid',
)


@_base_request_wrapper
class PaymeCreateTransactionRequestSerializer(serializers.Serializer):
    id = serializers.CharField(
        max_length=25,
        label="Transaction id",
        validators=[payment_id_validator]
    )
    time = MilisecTimestampField(label="Time", default=0)
    amount = serializers.DecimalField(max_digits=12, decimal_places=4)
    account = TransactionAccountRequestSerializer()


@_base_request_wrapper
class PaymePerformTransactionRequestSerializer(serializers.Serializer):
    id = serializers.CharField(
        max_length=25,
        label="Transaction id",
        validators=[payment_id_validator]
    )


PaymeCheckTransactionRequestSerializer = PaymePerformTransactionRequestSerializer


@_base_request_wrapper
class PaymeCancelTransactionRequestSerializer(serializers.Serializer):
    id = serializers.CharField(
        max_length=25,
        label="Transaction id",
        validators=[payment_id_validator]
    )
    reason = serializers.ChoiceField(choices=PaymeCancelReasonEnum.choices)


@_base_request_wrapper
class PaymeGetStatementMethodRequestSerializer(serializers.Serializer):
    from_time = MilisecTimestampField(source='from', default=0)
    to_time = MilisecTimestampField(source='to', default=0)

    def validate(self, data: OrderedDict):
        from_time = data['from']
        to_time = data['to']
        if from_time >= to_time:
            raise PaymeValidationError
        return data

    def get_fields(self):
        fields = super().get_fields()
        fields.update({
            'from': fields['from_time'],
            'to': fields['to_time'],
        })
        return fields


class PaymeTransactionStatementSerializer(BaseCustomModelSerializer):
    id = serializers.CharField(max_length=25, source='external_id', read_only=True)
    time = MilisecTimestampField(source='external_time', read_only=True, default=0)
    amount = serializers.FloatField(source='amount', read_only=True)
    account = TransactionAccountRequestSerializer(source='customer', read_only=True)
    create_time = MilisecTimestampField(default=0, source='date_add', read_only=True)
    perform_time = MilisecTimestampField(default=0, source='perform_time', read_only=True)
    cancel_time = MilisecTimestampField(default=0, source='cancel_time', read_only=True)
    transaction = serializers.IntegerField(source='pk', read_only=True)
    state = serializers.IntegerField(source='transaction_state', read_only=True)
    reason = serializers.IntegerField(allow_null=True, default=None, read_only=True)

    class Meta:
        model = PaymeTransactionModel
        fields = ('id', 'time', 'amount', 'account', 'create_time', 'perform_time',
                  'cancel_time', 'transaction', 'state', 'reason')


class PaymePaymentLogModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = PaymePaymentLogModel
        fields = '__all__'


class PaymePaymentGatewayModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = PaymePaymentGatewayModel
        fields = '__all__'

