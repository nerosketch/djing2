from rest_framework import serializers

from customers_legal import models
from djing2.lib.mixins import BaseCustomModelSerializer
from profiles.serializers import BaseAccountSerializer


class CustomerLegalModelSerializer(BaseAccountSerializer):
    balance = serializers.FloatField(read_only=True)

    class Meta:
        model = models.CustomerLegalModel
        fields = '__all__'


class LegalCustomerBankModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.LegalCustomerBankModel
        fields = '__all__'


class LegalCustomerPostAddressModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.LegalCustomerPostAddressModel
        fields = '__all__'


class LegalCustomerDeliveryAddressModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.LegalCustomerDeliveryAddressModel
        fields = '__all__'


class CustomerLegalTelephoneModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.CustomerLegalTelephoneModel
        fields = '__all__'
