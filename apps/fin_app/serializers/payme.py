from rest_framework import serializers
from rest_framework import status
from django.core.validators import integer_validator
from djing2.lib import IntEnumEx
from djing2.lib.mixins import BaseCustomModelSerializer
from fin_app.models.payme import PaymePaymentGatewayModel, PaymeErrorsEnum


def _base_request_wrapper(cls):
    class _PaymeBaseRequestSerializer(serializers.Serializer):
        method = serializers.CharField(label='Method', max_length=64)
        #  id = serializers.IntegerField(label='ID')
        params = cls

    return _PaymeBaseRequestSerializer


@_base_request_wrapper
class PaymeCheckPerformTransactionRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        label='Amount',
        required=True,
        max_digits=12,
        decimal_places=4
    )


@_base_request_wrapper
class PaymeCreateTransactionRequestSerializer(serializers.Serializer):
    pass
