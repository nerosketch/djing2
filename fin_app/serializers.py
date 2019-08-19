from rest_framework import serializers
from fin_app import models


class AllTimeGatewayModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PayAllTimeGateway
        fields = '__all__'


class AllTimePayLogModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AllTimePayLog
        fields = '__all__'
