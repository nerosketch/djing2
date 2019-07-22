from rest_framework.serializers import ModelSerializer
from networks.models import NetworkModel


class NetworkModelSerializer(ModelSerializer):

    class Meta:
        model = NetworkModel
        fields = '__all__'
