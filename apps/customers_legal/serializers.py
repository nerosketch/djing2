from rest_framework import serializers

from customers_legal import models


class CustomerLegalModelSerializer(serializers.ModelSerializer):
    balance = serializers.FloatField(read_only=True)

    class Meta:
        model = models.CustomerLegalModel
        exclude = ['password']


class LegalCustomerBankModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LegalCustomerBankModel
        fields = '__all__'


class LegalCustomerPostAddressModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LegalCustomerPostAddressModel
        fields = '__all__'


class LegalCustomerDeliveryAddressModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LegalCustomerDeliveryAddressModel
        fields = '__all__'


class CustomerLegalTelephoneModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CustomerLegalTelephoneModel
        fields = '__all__'

