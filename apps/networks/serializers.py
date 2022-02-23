from ipaddress import ip_network

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from netfields.rest_framework import MACAddressField

from djing2.lib.mixins import BaseCustomModelSerializer
from networks.models import NetworkIpPool, VlanIf, CustomerIpLeaseModel


class NetworkIpPoolModelSerializer(BaseCustomModelSerializer):
    kind_name = serializers.CharField(source="get_kind_display", read_only=True)
    # TODO: optimize
    usage_count = serializers.IntegerField(source="customeripleasemodel_set.count", read_only=True)

    vid = serializers.IntegerField(source="vlan_if.vid", read_only=True)

    @staticmethod
    def validate_network(value):
        if value is None:
            raise serializers.ValidationError(_("Network can not be empty"))
        try:
            net = ip_network(value, strict=False)
            return net.compressed
        except ValueError as e:
            raise serializers.ValidationError(e, code="invalid") from e

    class Meta:
        model = NetworkIpPool
        fields = "__all__"


class VlanIfModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = VlanIf
        fields = "__all__"


class CustomerIpLeaseModelSerializer(BaseCustomModelSerializer):
    is_dynamic = serializers.BooleanField(read_only=True)

    class Meta:
        model = CustomerIpLeaseModel
        fields = "__all__"


class FindCustomerByDeviceCredentialsParams(serializers.Serializer):
    mac = MACAddressField()
    dev_port = serializers.IntegerField(default=0)
