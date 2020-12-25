from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from sorm_export.models import (
    CommunicationStandardChoices,
    date_format, datetime_format
)


class CustomerIncrementalRootFormat(serializers.Serializer):
    customer_id = serializers.CharField(
        label=_('Customer id'),
        max_length=64,
        required=True
    )
    legal_customer_id = serializers.CharField(
        label=_('Legal customer id'),
        max_length=64,
        required=False
    )
    contract_start_date = serializers.DateField(
        label=_('Date of conclusion of the contract'),
        required=True,
        format=date_format
    )  # format dd.mm.YYYY
    customer_login = serializers.CharField(  # same as id
        label=_('Customer login'),
        max_length=256,
        required=True
    )
    customer_state = serializers.CharField(default='')  # reserved
    communication_standard = serializers.ChoiceField(
        label=_('Communication_standard'),
        choices=CommunicationStandardChoices.choices,
        default=0
    )


class CustomerIncrementalContractFormat(serializers.Serializer):
    contract_id = serializers.CharField(
        label=_('Contract ID'),
        max_length=64,
        required=True
    )
    customer_id = serializers.CharField(
        label=_('Customer id'),
        max_length=64,
        required=True
    )
    contract_status = serializers.CharField(default='', required=False)  # reserved
    contract_start_date = serializers.DateField(
        label=_('Date of conclusion of the contract'),
        required=True,
        format=date_format
    )  # format dd.mm.YYYY
    contract_end_date = serializers.DateTimeField(
        label=_('Contract completion date'),
        format=datetime_format,
        allow_null=True,
        required=False
    )  # format DD.mm.YYYYTHH:MM:SS or ''
    contract_number = serializers.CharField(
        label=_('Contract number'),
        max_length=128,
        required=False
    )
    contract_title = serializers.CharField(
        label=_('Contract title'),
        max_length=256,
        default=''
    )
