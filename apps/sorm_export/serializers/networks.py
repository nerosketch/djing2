from django.db import models
from django.utils.translation import gettext_lazy as _
from netfields.rest_framework import MACAddressField
from rest_framework import serializers

from sorm_export.models import datetime_format


class IpLeaseAddrTypeChoice(models.IntegerChoices):
    GRAY = 0, _('Gray addr')
    WHITE = 1, _('White addr')
    VPN = 3, _('VPN addr')


class CustomerIpLeaseExportFormat(serializers.Serializer):
    ap_id = serializers.CharField(default='', allow_blank=True)  # Reserved
    customer_id = serializers.CharField(
        label=_('Customer id'),
        max_length=64,
        required=True
    )  # CustomerRootObjectFormat.legal_customer_id
    ip_addr = serializers.IPAddressField(
        required=True
    )
    ip_addr_type = serializers.ChoiceField(
        choices=IpLeaseAddrTypeChoice.choices,
        required=True
    )
    assign_time = serializers.DateTimeField(
        format=datetime_format,
        required=True
    )
    dead_time = serializers.DateTimeField(
        format=datetime_format,
        required=False,
        allow_null=True
    )
    mac_addr = MACAddressField(
        required=False,
        default=None,
        allow_null=True
    )
