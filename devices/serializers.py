from rest_framework.serializers import ModelSerializer
from devices.models import Device, Port


class DeviceModelSerializer(ModelSerializer):
    class Meta:
        model = Device
        fields = (
            'pk', 'ip_address', 'mac_addr', 'comment',
            'dev_type', 'man_passw', 'parent_dev', 'snmp_extra',
            'extra_data', 'status', 'is_noticeable'
        )


class PortModelSerializer(ModelSerializer):
    class Meta:
        model = Port
        fields = ('pk', 'device', 'num', 'descr')
