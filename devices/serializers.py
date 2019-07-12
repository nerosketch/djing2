from rest_framework.serializers import (
    ModelSerializer, IntegerField,
    CharField, DictField, ListField, PrimaryKeyRelatedField
)
from devices.models import Device, Port
from groupapp.models import Group


class DeviceModelSerializer(ModelSerializer):
    dev_type_str = CharField(source='get_dev_type_display', read_only=True)
    parent_dev_name = CharField(source='parent_dev.comment', allow_null=True, read_only=True)
    parent_dev_group = IntegerField(source='parent_dev.group.pk', allow_null=True, read_only=True)
    attached_users = ListField(
        source='customer_set.all', read_only=True,
        child=PrimaryKeyRelatedField(read_only=True)
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
        fields = ['pk', 'device', 'num', 'descr']


class PortModelSerializerExtended(PortModelSerializer):
    user_count = IntegerField(
        source='customer_set.count',
        read_only=True
    )
    additional = DictField(
        source='scan_additional',
        read_only=True
    )

    class Meta(PortModelSerializer.Meta):
        fields = PortModelSerializer.Meta.fields + ['user_count', 'additional']


class DeviceGroupsModelSerializer(ModelSerializer):
    device_count = IntegerField(
        source='device_set.count',
        read_only=True
    )

    class Meta:
        model = Group
        fields = ('pk', 'title', 'code', 'device_count')
