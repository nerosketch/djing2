from collections import OrderedDict

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from devices.models import Device, Port, PortVlanMemberModel
from djing2.lib.mixins import BaseCustomModelSerializer
from groupapp.models import Group


class AttachedUserSerializer(serializers.Serializer):
    pk = serializers.PrimaryKeyRelatedField(read_only=True)
    full_name = serializers.CharField(source="get_full_name", read_only=True)


class DeviceModelSerializer(BaseCustomModelSerializer):
    dev_type_str = serializers.CharField(source="get_dev_type_display", read_only=True)
    iface_name = serializers.CharField(source="get_if_name", read_only=True)
    parent_dev_name = serializers.CharField(source="parent_dev", allow_null=True, read_only=True)
    parent_dev_group = serializers.IntegerField(source="parent_dev.group_pk", allow_null=True, read_only=True)

    attached_users = serializers.ListField(source="customer_set.all", read_only=True, child=AttachedUserSerializer())

    class Meta:
        model = Device
        depth = 0
        fields = (
            "pk",
            "ip_address",
            "mac_addr",
            "comment",
            "dev_type",
            "dev_type_str",
            "man_passw",
            "group",
            "parent_dev",
            "parent_dev_name",
            "parent_dev_group",
            "snmp_extra",
            "attached_users",
            "iface_name",
            "extra_data",
            "status",
            "is_noticeable",
            "code",
            "sites",
        )
        extra_kwargs = {"ip_address": {"required": False}}


class DevicePONModelSerializer(DeviceModelSerializer):
    class Meta(DeviceModelSerializer.Meta):
        pass


class DeviceWithoutGroupModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = Device
        fields = (
            "pk",
            "ip_address",
            "mac_addr",
            "comment",
            "dev_type",
            "man_passw",
            "parent_dev",
            "snmp_extra",
            "status",
            "is_noticeable",
            "sites",
        )


class PortModelSerializer(BaseCustomModelSerializer):
    user_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Port
        fields = ("pk", "device", "num", "descr", "user_count")


class PortVlanConfigMemberSerializer(serializers.Serializer):
    vid = serializers.IntegerField(min_value=1, max_value=4095, required=True)
    # title = serializers.CharField(max_length=128, required=False)
    is_management = serializers.BooleanField(default=False, initial=False, allow_null=True)
    # native = serializers.BooleanField(default=False, initial=False)


class PortVlanConfigSerializer(serializers.Serializer):
    port = serializers.IntegerField(min_value=1, max_value=28)
    vids = PortVlanConfigMemberSerializer(many=True)


class DeviceGroupsModelSerializer(BaseCustomModelSerializer):
    device_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Group
        fields = ("pk", "title", "code", "device_count")


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
