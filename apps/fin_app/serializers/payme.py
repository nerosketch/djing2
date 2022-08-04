from collections import OrderedDict
from django.utils.translation import gettext_lazy as _
from django.utils.regex_helper import _lazy_re_compile
from django.core.validators import integer_validator, RegexValidator
from rest_framework import serializers
from djing2.lib.mixins import BaseCustomModelSerializer
from djing2.serializers import TimestampField
from fin_app.models.payme import (
    PaymeCancelReasonEnum, PaymeTransactionModel,
    PaymeValidationError
)


def _base_request_wrapper(cls):
    class _PaymeBaseRequestSerializer(serializers.Serializer):
        method = serializers.CharField(label='Method', max_length=64)
        #  id = serializers.IntegerField(label='ID')
        params = cls

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
    time = TimestampField("Time")
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
    from_time = TimestampField(source='from')
    to_time = TimestampField(source='to')

    def validate(self, data: OrderedDict):
        from_time = data['from_time']
        to_time = data['to_time']
        if from_time >= to_time:
            raise PaymeValidationError
        return data


class PaymeTransactionStatementSerializer(BaseCustomModelSerializer):
    id = serializers.CharField(max_length=25, source='external_id', readonly=True)
    time = TimestampField(source='external_time', readonly=True)
    amount = serializers.IntegerField(source='amount', readonly=True)
    account = TransactionAccountRequestSerializer(source='customer', readonly=True)
    create_time = TimestampField(default=0, source='create_time', readonly=True)
    perform_time = TimestampField(default=0, source='perform_time', readonly=True)
    cancel_time = TimestampField(default=0, source='cancel_time', readonly=True)
    transaction = serializers.CharField(source='pk', readonly=True)
    state = serializers.IntegerField(source='transaction_state', readonly=True)
    reason = serializers.IntegerField(null=True, default=None, readonly=True)

    class Meta:
        model = PaymeTransactionModel
        fields = '__all__'

