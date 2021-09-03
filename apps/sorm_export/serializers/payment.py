from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
# from netfields.rest_framework import MACAddressField

from sorm_export.models import datetime_format


class UnknownPaymentExportFormat(serializers.Serializer):
    customer_id = serializers.CharField(
        label=_('Customer id'),
        max_length=64,
        required=True
    )  # CustomerRootObjectFormat.legal_customer_id
    customer_code = serializers.CharField(default='', allow_blank=True)  # reserved
    pay_time = serializers.DateTimeField(
        label=_('Payment time'),
        format=datetime_format,
        required=True
    )
    amount = serializers.DecimalField(
        label=_('Pay amount'),
        required=True,
        max_digits=9,
        decimal_places=2
    )
    """
    https://wiki.vasexperts.ru/doku.php?id=sorm:sorm3:sorm3_subs_dump:sorm3_subs_pays:unknown_payment
    """
    pay_description = serializers.CharField(
        max_length=256,
        required=True,
        label='Тип платежа (способ оплаты)',
        help_text='Строка, размер 256, например, «Безналичный»'
    )
    pay_params = serializers.CharField(
        max_length=512,
        required=False,
        allow_null=True,
        allow_blank=True,
        label='неструктурированная» информация',
        help_text="параметры платежа, строка, размер 512, дополнительная информация "
                  "по платежу в неструктурированном виде, при её наличии, например "
                  "«Терминал Киви на Бронницкой, д.1 и идентификатор платежа в этом операторе платеж»"
    )


# class TeminalPaymentExportFormat(GeneralFieldsMixin, serializers.Serializer):
#     """
#     https://wiki.vasexperts.ru/doku.php?id=sorm:sorm3:sorm3_subs_dump:sorm3_subs_pays:terminal_charge
#     TODO: Узнать о правилах выгрузки, почему если координаты отсутствуют то все поля должны быть пусты.
#     TODO: Если у нас никогда нет гео координат, то нам можно не делать эту выгрузку?
#     """
#     provider_title = serializers.CharField(
#         label='название оператора платежа',
#         default='',
#         required=False
#     )  # reserved
#     terminal_num = serializers.IntegerField(
#         label='номер платёжного терминала',
#         required=True,
#         min_value=10
#     )
#     mobile_zone_num = serializers.IntegerField(
#         required=False,
#         allow_null=True
#     )
#     bsid = serializers.IntegerField(
#         label='идентификатор базовой станции',
#         required=False
#     )
#     timing_advance = serializers.IntegerField(
#         label='временная компенсация',
#         min_value=0,
#         max_value=63,
#         required=False
#     )
#     sector_id = serializers.CharField(
#         label='идентификатор сектора',
#         max_length=64,
#         required=False,
#         default=''
#     )
#     device_mac = MACAddressField(
#         label='MAC-адрес сетевого оборудования сектора',
#         required=False,
#         default=None,
#         allow_null=True
#     )
    # geo_id = serializers.
    # TODO: ... остальные поля сделать после того как узнаю нужно-ли это
