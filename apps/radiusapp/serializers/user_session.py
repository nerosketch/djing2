from rest_framework import serializers

from radiusapp.models import CustomerRadiusSession


class CustomerRadiusSessionModelSerializer(serializers.ModelSerializer):
    h_input_octets = serializers.CharField(read_only=True)
    h_output_octets = serializers.CharField(read_only=True)
    h_input_packets = serializers.CharField(read_only=True)
    h_output_packets = serializers.CharField(read_only=True)
    ip_lease_ip = serializers.IPAddressField(source="ip_lease.ip_address", read_only=True)
    ip_lease_mac = serializers.IPAddressField(source="ip_lease.mac_address", read_only=True)
    # is_guest_session = serializers.BooleanField(read_only=True)

    def create(self, validated_data):
        # readonly model
        pass

    def update(self, instance, validated_data):
        # readonly model
        pass

    class Meta:
        model = CustomerRadiusSession
        exclude = ["customer"]
