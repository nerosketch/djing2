from rest_framework.serializers import ModelSerializer, IntegerField
from devices.models import Device, Port
from groupapp.models import Group


class DeviceModelSerializer(ModelSerializer):
    class Meta:
        model = Device
        fields = (
            'pk', 'ip_address', 'mac_addr', 'comment',
            'dev_type', 'man_passw', 'group', 'parent_dev', 'snmp_extra',
            'extra_data', 'status', 'is_noticeable'
        )


class DeviceWithoutGroupModelSerializer(ModelSerializer):
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


class DeviceGroupsModelSerializer(ModelSerializer):
    device_count = IntegerField(
        source='device_set.count',
        read_only=True
    )

    class Meta:
        model = Group
        fields = ('pk', 'title', 'code', 'device_count')
