from rest_framework import serializers
from dynamicfields.models import FieldModel


class FieldModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = FieldModel
        fields = '__all__'
