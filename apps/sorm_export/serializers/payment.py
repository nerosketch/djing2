from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

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
        max_digits=11,
        decimal_places=6
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
