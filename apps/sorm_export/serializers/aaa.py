from datetime import datetime
from rest_framework import serializers
from sorm_export.models import datetime_format
from django.db.models import IntegerChoices
from django.utils.translation import gettext_lazy as _


AAA_EXPORT_FNAME = "/tmp/aaa_export_fname.txt"


class AAAEventType(IntegerChoices):
    RADIUS_AUTH_START = 0, "Auth acct start event"
    RADIUS_AUTH_STOP = 1, "Auth acct stop event"
    RADIUS_AUTH_UPDATE = 2, "Auth acct update event"


class AAAConnectionType(IntegerChoices):
    BROADBAND_ACCESS = 0, "ШПД соединение"
    OUT_DIAL = 1, _("Ouput voip dial")
    INPUT_DIAL = 2, _("Input voip dial")


class AAAExportSerializer(serializers.Serializer):
    event_time = serializers.DateTimeField(format=datetime_format, default=lambda: datetime.now())
    event_type = serializers.ChoiceField(choices=AAAEventType.choices, required=True)
    session_id = serializers.CharField(required=True)
    customer_ip = serializers.IPAddressField(required=True)
    customer_db_username = serializers.CharField(required=True)
    connection_type = serializers.ChoiceField(
        choices=AAAConnectionType.choices, default=AAAConnectionType.BROADBAND_ACCESS
    )
    input_telephone_number = serializers.CharField(default="")
    output_telephone_number = serializers.CharField(default="")
    nas_ip_addr = serializers.IPAddressField(
        default="0.0.0.0",
    )
    nas_port = serializers.IntegerField(default=0)
    input_octets = serializers.IntegerField(default=0)
    output_octets = serializers.IntegerField(default=0)
    customer_password = serializers.CharField(default="")
    customer_device_mac = serializers.CharField(default="", allow_blank=True)
    apn_string = serializers.CharField(default="")
    device_point_id = serializers.IntegerField(default=0)
