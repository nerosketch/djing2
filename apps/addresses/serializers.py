from djing2.lib.mixins import BaseCustomModelSerializer
from addresses.models import AddressModel


class AddressModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = AddressModel
        fields = '__all__'
