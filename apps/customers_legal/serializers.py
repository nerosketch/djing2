from rest_framework import serializers

from customers_legal.models import CustomerLegalModel


class CustomerLegalModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerLegalModel
        fields = '__all__'
