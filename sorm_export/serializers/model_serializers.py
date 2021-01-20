from rest_framework import serializers
from sorm_export import models


class FiasRecursiveAddressModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FiasRecursiveAddressModel
        fields = '__all__'
