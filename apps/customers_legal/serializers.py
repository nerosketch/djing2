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
        exclude = ('number',)


class CustomerLegalTelephoneModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.CustomerLegalTelephoneModel
        fields = '__all__'
