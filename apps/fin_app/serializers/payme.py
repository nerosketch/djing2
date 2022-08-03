from django.utils.translation import gettext_lazy as _
from django.utils.regex_helper import _lazy_re_compile
from django.core.validators import integer_validator, RegexValidator
from rest_framework import serializers
from rest_framework import status
from djing2.lib import IntEnumEx
from djing2.lib.mixins import BaseCustomModelSerializer
from djing2.serializers import TimestampField
from fin_app.models.payme import PaymeCancelReasonEnum


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

