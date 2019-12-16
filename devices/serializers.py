from rest_framework import serializers
from devices.models import Device, Port
from djing2.lib.mixins import BaseCustomModelSerializer
from groupapp.models import Group


class DeviceModelSerializer(BaseCustomModelSerializer):
    dev_type_str = serializers.CharField(source='get_dev_type_display', read_only=True)
    parent_dev_name = serializers.CharField(source='parent_dev.comment', allow_null=True, read_only=True)
    parent_dev_group = serializers.IntegerField(source='parent_dev.group.pk', allow_null=True, read_only=True)
    attached_users = serializers.ListField(
        source='customer_set.all', read_only=True,
        child=serializers.PrimaryKeyRelatedField(read_only=True)
    )

    class Meta:
        model = Device
        fields = (
            'pk', 'ip_address', 'mac_addr', 'comment',
            'dev_type', 'dev_type_str', 'man_passw', 'group',
            'parent_dev', 'parent_dev_name', 'parent_dev_group',
            'snmp_extra', 'attached_users',
            'extra_data', 'status', 'is_noticeable'
        )


class DeviceWithoutGroupModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = Device
        fields = (
            'pk', 'ip_address', 'mac_addr', 'comment',
            'dev_type', 'man_passw', 'parent_dev', 'snmp_extra',
            'extra_data', 'status', 'is_noticeable'
        )


class PortModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = Port
        fields = ['pk', 'device', 'num', 'descr']


class PortModelSerializerExtended(PortModelSerializer):
    user_count = serializers.IntegerField(
        source='customer_set.count',
        read_only=True
    )
    additional = serializers.DictField(
        source='scan_additional',
        read_only=True
    )

    class Meta(PortModelSerializer.Meta):
        fields = PortModelSerializer.Meta.fields + ['user_count', 'additional']


class DeviceGroupsModelSerializer(BaseCustomModelSerializer):
    device_count = serializers.IntegerField(
        source='device_set.count',
        read_only=True
    )

    class Meta:
        model = Group
        fields = ('pk', 'title', 'code', 'device_count')
