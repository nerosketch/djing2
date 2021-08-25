from django.db import models
from rest_framework import serializers
from sorm_export.models import datetime_format
from gateways.models import GatewayClassChoices


class GatewayExportFormatSerializer(serializers.Serializer):
    # https://wiki.vasexperts.ru/doku.php?id=sorm:sorm3:sorm3_subs_dump:sorm3_subs_gateways:start
    gw_id = serializers.IntegerField(
        label="ИД шлюза",
        help_text="число, содержит уникальный идентификатор шлюза",
        required=True
    )
    gw_type = serializers.ChoiceField(
        label="тип шлюза",
        choices=[(v, v) for k, v in GatewayClassChoices.choices]
    )
    descr = serializers.CharField(
        label='Описание',
        max_length=256,
        required=True
    )
    gw_addr = serializers.CharField(
        label="адрес шлюза",
        help_text="содержит адрес шлюза в неструктурированном виде",
        max_length=1024,
        required=True
    )
    start_use_time = serializers.DateTimeField(
        label="дата установки шлюза",
        format=datetime_format,
        required=True,
    )
    deactivate_time = serializers.DateTimeField(
        label="дата демонтажа шлюза",
        format=datetime_format,
        required=False,
        default='',
        allow_null=True,
    )
    ip_addrs = serializers.CharField(
        label="список IP-адресов и портов шлюзов",
        help_text=("перечисление IPv4/IPv6-адресов с указанием порта через запятую без пробелов в формате "
                   "«<IPv4/[IPv6]>:<port>», IPv6 - в квадратных скобках"),
        required=True,
        max_length=1024
    )
