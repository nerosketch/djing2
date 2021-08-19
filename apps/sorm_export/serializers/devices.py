from rest_framework import serializers
from django.db import models
from sorm_export.models import datetime_format, CommunicationStandardChoices


class DeviceSwitchTypeChoices(models.Choices):
    INTERNAL = 'internal'
    BORDER = 'border'


class DeviceSwitchExportFormat(serializers.Serializer):
    # https://wiki.vasexperts.ru/doku.php?id=sorm:sorm3:sorm3_subs_dump:sorm3_subs_switch:start

    title = serializers.CharField(
        max_length=128,
        required=True,
        label="Наименование коммутатора",
        help_text="строка, размер 128, содержит уникальный идентификатор коммутатора"
    )
    switch_type = serializers.ChoiceField(
        choices=DeviceSwitchTypeChoices.choices,
        required=True,
        label="тип коммутатора",
        help_text=("строка, размер 512, справочник: «internal» - внутренний коммутатор, «border» - пограничный "
                   "коммутатор")
    )
    network_type = serializers.ChoiceField(
        choices=CommunicationStandardChoices.choices,
        required=True,
        label="Тип сети",
        help_text=("строка, размер 128, справочник: «unknown» - неизвестная сеть, «GSM» - GSM, «CDMA» - CDMA, "
                   "«PSTN» - ТФоП-сеть, «Ethernet» - стационарная сеть передачи данных, «TMC» - ТМС-служба, "
                   "«mobile» - мобильная сеть, «WIFI» - WiFi-сеть, «WIMAX» - WiMAX-сеть, «paging» - "
                   "персональный радиовызов")
    )
    description = serializers.CharField(
        max_length=256,
        required=True,
        label="описание",
        help_text="строка, размер 256"
    )
    place = serializers.CharField(
        max_length=1024,
        label="строка, размер 1024,",
        help_text="содержит адрес установки коммутатора в неструктурированном виде",
        required=True,
    )
    telephone_identifier = serializers.CharField(default='')
    start_usage_time = serializers.DateTimeField(
        format=datetime_format,
        required=True,
        label="дата установки коммутатора",
        help_text="дата, формат DD.mm.YYYYTHH:MM:SS",
    )
    end_usage_time = serializers.DateTimeField(
        format=datetime_format,
        required=False,
        allow_null=True,
        default='',
        label="дата демонтажа коммутатора",
        help_text="дата, формат DD.mm.YYYYTHH:MM:SS",
    )
