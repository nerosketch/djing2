from django.core import validators
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from sorm_export.models import (
    CommunicationStandardChoices,
    CustomerTypeChoices,
    CustomerDocumentTypeChoices, Choice4BooleanField
)

_date_format = '%d.%m.%Y'
_datetime_format = '%d.%m.%YT%H:%M:%S'


class CustomerExportFormat(serializers.Serializer):
    # https://wiki.vasexperts.ru/doku.php?id=sorm:sorm3:sorm3_subs_dump:sorm3_subs_plain:start

    # def __init__(self, *args, **kwargs):
    #     kwargs['read_only'] = True
    #     super().__init__(*args, **kwargs)

    communication_standard = serializers.ChoiceField(
        label=_('Communication_standard'),
        choices=CommunicationStandardChoices.choices,
        default=0
    )
    customer_id = serializers.CharField(
        label=_('Contract id'),
        max_length=128,
        required=True
    )
    customer_login = serializers.CharField(
        label=_('Customer login'),
        max_length=64,
        allow_blank=True,
        required=False,
    )
    contract_number = serializers.CharField(
        label=_('Contract number'),
        max_length=64,
        required=True
    )
    current_state = serializers.ChoiceField(
        label=_('Current state'),
        choices=Choice4BooleanField.choices,
        required=True
    )  # '0' or '1'
    contract_start_date = serializers.DateTimeField(
        label=_('Date of conclusion of the contract'),
        required=True,
        format=_datetime_format
    )  # format DD.mm.YYYYTHH:MM:SS
    contract_end_date = serializers.DateTimeField(
        label=_('Contract completion date'),
        format=_datetime_format,
        allow_null=True
    )  # format DD.mm.YYYYTHH:MM:SS or ''
    customer_type = serializers.ChoiceField(
        label=_('Customer type'),
        choices=CustomerTypeChoices.choices,
        required=True
    )
    name_structured_type = serializers.ChoiceField(
        label=_('Name structured type'),
        choices=Choice4BooleanField.choices,
        required=False
    )  # '0' or '1'
    name = serializers.CharField(
        label=_('Name'),
        max_length=64,
        allow_blank=True,
        required=False
    )
    surname = serializers.CharField(
        label=_('Surname'),
        max_length=64,
        allow_blank=True,
        required=False
    )
    second_name = serializers.CharField(
        label=_('Second name'),
        max_length=64,
        allow_blank=True,
        required=False
    )
    not_structured_name = serializers.CharField(
        label=_('Not structured name'),
        max_length=182,
        help_text=_('Fio from customer model'),
        allow_blank=True,
        required=False
    )
    birthday = serializers.DateField(
        label=_('Birthday'),
        required=True,
        format=_date_format
    )  # format DD.mm.YYYY
    passport_type_structured = serializers.ChoiceField(
        label=_('Is structured data'),
        choices=Choice4BooleanField.choices,
        required=True
    )
    passport_serial = serializers.CharField(
        label=_('Passport serial'),
        max_length=32,
        validators=[validators.integer_validator],
        required=True
    )
    passport_number = serializers.CharField(
        label=_('Passport number'),
        max_length=64,
        validators=[validators.integer_validator],
        required=True
    )
    passport_date = serializers.DateField(
        label=_('Passport date'),
        format=_date_format,
        required=True
    )
    passport_distributor = serializers.CharField(
        label=_('Passport distributor'),
        max_length=128,
        required=True
    )
    passport_unstructured = serializers.CharField(default='')  # reserved
    document_type = serializers.ChoiceField(
        label=_('Passport document type'),
        required=True,
        choices=CustomerDocumentTypeChoices.choices
    )
    customer_bank = serializers.CharField(
        label=_('Customer bank'),
        max_length=256,
        allow_blank=True,
        required=False
    )
    customer_bank_num = serializers.CharField(
        label=_('Bank receipt number'),
        max_length=128,
        allow_blank=True,
        required=False
    )
    # TODO: finish fields
