from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from sorm_export.models import date_format, CommunicationStandardChoices


class ServiceIncrementalNomenclature(serializers.Serializer):
    # https://wiki.vasexperts.ru/doku.php?id=sorm:sorm3:sorm3_subs_dump:sorm3_subs_serv_list:service_list:start
    service_id = serializers.IntegerField(
        label=_('Service id'),
        required=True,
        max_value=0xffffffff,
        min_value=0
    )
    mnemonic = serializers.CharField(
        label='Название услуги',
        required=True,
        max_length=64
    )
    description = serializers.CharField(
        label=_('Service description'),
        max_length=256,
        required=False,
        default=''
    )
    begin_time = serializers.DateField(
        label='Дата активации услуги',
        format=date_format,
        required=True
    )
    end_time = serializers.DateField(
        label='Дата деактивации услуги',
        format=date_format,
        required=False,
        allow_null=True
    )
    operator_type_id = serializers.CharField(
        label=_('Operator type id'),
        default=CommunicationStandardChoices.ETHERNET.label
    )
