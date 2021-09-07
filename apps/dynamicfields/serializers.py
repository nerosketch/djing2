from rest_framework import serializers
from dynamicfields.models import FieldModel


class FieldModelSerializer(serializers.ModelSerializer):
    field_type_name = serializers.CharField(read_only=True, source='get_field_type_display')

    class Meta:
        model = FieldModel
        fields = '__all__'
