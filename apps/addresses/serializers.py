from rest_framework import serializers
from djing2.lib.mixins import BaseCustomModelSerializer
from addresses.models import AddressModel


class AddressModelSerializer(BaseCustomModelSerializer):
    parent_addr_title = serializers.CharField(source='parent_addr.title', read_only=True)

    class Meta:
        model = AddressModel
        fields = '__all__'
