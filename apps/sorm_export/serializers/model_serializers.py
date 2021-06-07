from rest_framework import serializers
from sorm_export import models


class FiasRecursiveAddressModelSerializer(serializers.ModelSerializer):
    ao_level_name = serializers.CharField(source='get_ao_level_display', read_only=True)
    ao_type_name = serializers.CharField(source='get_ao_type_display', read_only=True)

    class Meta:
        model = models.FiasRecursiveAddressModel
        fields = '__all__'
