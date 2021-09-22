from rest_framework import serializers

from sorm_export.models import FiasRecursiveAddressModel


удалить после удаления FiasRecursiveAddressModel
class FiasRecursiveAddressModelSerializer(serializers.ModelSerializer):
    ao_level_name = serializers.CharField(source='get_ao_level_display', read_only=True)
    ao_type_name = serializers.CharField(source='get_ao_type_display', read_only=True)
    parent_ao_name = serializers.CharField(source='parent_ao.title', read_only=True)
    locality_title = serializers.CharField(source='locality.title', read_only=True поправить)

    class Meta:
        model = FiasRecursiveAddressModel
        fields = '__all__'
