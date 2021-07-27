from rest_framework import serializers

from djing2.lib.mixins import BaseCustomModelSerializer
from maps.models import DotModel


class DotModelSerializer(BaseCustomModelSerializer):

    class Meta:
        model = DotModel
        fields = '__all__'
