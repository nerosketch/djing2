from rest_framework import serializers
from djing2.lib.mixins import BaseCustomModelSerializer
from addresses.models import AddressModel


class AddressModelSerializer(BaseCustomModelSerializer):
    parent_addr_title = serializers.CharField(source='parent_addr.title', read_only=True)
    fias_address_level_name = serializers.CharField(source='get_fias_address_level_display', read_only=True)
    fias_address_type_name = serializers.CharField(source='get_fias_address_type_display', read_only=True)

    class Meta:
        model = AddressModel
        fields = '__all__'
