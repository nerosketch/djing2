from django.core.validators import validate_ipv46_address, integer_validator
from rest_framework import serializers
from sorm_export.models import datetime_format


class SpecialNumbersSerializerFormat(serializers.Serializer):
    tel_number = serializers.CharField(
        validators=[integer_validator]
    )
    ip_address = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        validators=[validate_ipv46_address]
    )
    description = serializers.CharField(
        required=True
    )
    start_time = serializers.DateTimeField(
        required=True,
        format=datetime_format,
    )
    end_time = serializers.DateTimeField(
        required=False,
        allow_null=True,
        format=datetime_format,
        default=''
    )

