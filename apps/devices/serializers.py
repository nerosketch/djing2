from collections import OrderedDict

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from djing2.lib.mixins import BaseCustomModelSerializer
from devices.models import Device, Port, PortVlanMemberModel
from groupapp.models import Group


class AttachedUserSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(read_only=True)
    full_name = serializers.CharField(source="get_full_name", read_only=True)


class DeviceModelSerializer(BaseCustomModelSerializer):
    dev_type_str = serializers.CharField(source="get_dev_type_display", read_only=True)
    iface_name = serializers.CharField(source="get_if_name", read_only=True)
    parent_dev_name = serializers.CharField(source="parent_dev", allow_null=True, read_only=True)
    parent_dev_group = serializers.IntegerField(source="parent_dev.group_pk", allow_null=True, read_only=True)
    address_title = serializers.CharField(source='get_address', read_only=True)
    attached_users = serializers.ListField(source="customer_set.all", read_only=True, child=AttachedUserSerializer())

    class Meta:
        model = Device
        depth = 0
        exclude = ('vlans',)
        extra_kwargs = {"ip_address": {"required": False}}


class DevicePONModelSerializer(DeviceModelSerializer):
    class Meta(DeviceModelSerializer.Meta):
        pass


class DeviceWithoutGroupModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = Device
        exclude = [
            'group',
            'extra_data',
            'vlans',
            'code',
            'create_time',
        ]


class PortModelSerializer(BaseCustomModelSerializer):
    user_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Port
        fields = ("id", "device", "num", "descr", "user_count")


class PortVlanMemberModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = PortVlanMemberModel
        fields = "__all__"


class DevOnuVlan(serializers.Serializer):
    vid = serializers.IntegerField(default=1)
    native = serializers.BooleanField(default=False)


class DevOnuVlanInfoTemplate(serializers.Serializer):
    port = serializers.IntegerField(default=1)
    vids = DevOnuVlan(many=True)


class DeviceOnuConfigTemplate(serializers.Serializer):
    configTypeCode = serializers.CharField(label=_("Config code"), max_length=64)
    vlanConfig = serializers.ListField(child=DevOnuVlanInfoTemplate(), allow_empty=False)

    def validate(self, data: OrderedDict):
        vlan_config = data.get("vlanConfig")
        if not vlan_config:
            raise serializers.ValidationError("vlanConfig can not be empty")
        # TODO: Add validations
        return data


class GroupsWithDevicesSerializer(serializers.ModelSerializer):
    device_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Group
        fields = ("id", "title", "device_count")
