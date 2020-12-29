from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from sorm_export.models import datetime_format


class CustomerServiceIncrementalFormat(serializers.Serializer):
    service_id = serializers.IntegerField(
        label=_('Service id'),
        required=True,
        max_value=0xffffffff,
        min_value=0
    )
    customer_id = serializers.CharField(
        label=_('Customer id'),
        max_length=128,
        required=True
    )
    personal_account_id = serializers.CharField(default='', required=False)  # reserved
    ap_id = serializers.CharField(default='', required=False)  # reserved
    contract_id = serializers.CharField(default='', required=False)  # reserved

    parameter = serializers.CharField(
        label='Индивидуальные параметры настройки услуги абонента',
        max_length=256,
        required=True
    )
    begin_time = serializers.DateTimeField(
        label='Дата подключения услуги',
        help_text='дата подключения первой услуги должна быть равна дате заключения контракта',
        format=datetime_format,
        required=True
    )
    end_time = serializers.DateTimeField(
        label='Дата отключения услуги',
        format=datetime_format,
        required=False,
        allow_null=True
    )
