from django.utils.translation import gettext_lazy as _
from netfields.rest_framework import MACAddressField
from rest_framework import serializers


class _RadiusOpt82Serializer(serializers.Serializer):
    remote_id = serializers.CharField(label=_('remote id'), required=True)
    circuit_id = serializers.CharField(label=_('circuit id'), required=True)


class RadiusDHCPRequestSerializer(serializers.Serializer):
    opt82 = _RadiusOpt82Serializer(label=_('Option82'))
    client_mac = MACAddressField(label=_('Client mac address'))
    pool_tag = serializers.CharField(label=_('Location pool tag'),
                                     max_length=32, allow_blank=True,
                                     allow_null=True, default=None)
