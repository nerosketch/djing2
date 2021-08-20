from rest_framework import serializers
from netfields.rest_framework import CidrAddressField
from sorm_export.models import datetime_format


class IpNumberingExportFormatSerializer(serializers.Serializer):
    ip_net = CidtAddressField()
    descr = serializers.CharField(
        max_length=256,
        required=True,
        # validators=[]
    )
    start_usage_time = serializers.DateTimeField(
        format=datetime_format,
        required=True,
    )
    end_usage_time = serializers.DateTimeField(
        format=datetime_format,
        required=False,
        allow_null=True,
        allow_blank=True,
        default=''
    )
