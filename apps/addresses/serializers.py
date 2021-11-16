from collections import OrderedDict
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from djing2.lib.mixins import BaseCustomModelSerializer
from addresses.models import AddressModel, AddressModelTypes


class AddressModelSerializer(BaseCustomModelSerializer):
    parent_addr_title = serializers.CharField(source='parent_addr.title', read_only=True)
    fias_address_level_name = serializers.CharField(source='get_fias_address_level_display', read_only=True)
    fias_address_type_name = serializers.CharField(source='get_fias_address_type_display', read_only=True)

    def validate_title(self, value: str):
        address_type = self.initial_data.get('address_type')
        if not address_type:
            raise serializers.ValidationError("address_type can not be empty")
        # Квартиры, дома, номера офисов могут быть только числовыми
        addr_num_types = (
            AddressModelTypes.HOUSE.value,
            AddressModelTypes.OFFICE_NUM.value,
        )
        if address_type in addr_num_types:
            title = value.strip()
            try:
                int(title)
            except ValueError:
                raise serializers.ValidationError(_("House and office can be only number"))
        return value

    def validate(self, data: OrderedDict):
        # Улица не может находится в улице
        return data

    class Meta:
        model = AddressModel
        fields = '__all__'
