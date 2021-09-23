from rest_framework import serializers

from sorm_export.models import FiasRecursiveAddressModel


class FiasRecursiveAddressModelSerializer(serializers.ModelSerializer):
    fias_address_level_name = serializers.CharField(source='get_fias_address_level_display', read_only=True)
    fias_address_type_name = serializers.CharField(source='get_fias_address_type_display', read_only=True)

    class Meta:
        model = FiasRecursiveAddressModel
        fields = '__all__'
