from rest_framework import serializers
from djing2.lib.mixins import BaseCustomModelSerializer
from fin_app import models


class AllTimeGatewayModelSerializer(BaseCustomModelSerializer):
    pay_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.PayAllTimeGateway
        fields = '__all__'


class AllTimePayLogModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.AllTimePayLog
        fields = '__all__'


class PayAllTimeGatewayModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.PayAllTimeGateway
        fields = '__all__'
