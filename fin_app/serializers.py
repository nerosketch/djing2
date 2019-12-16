from djing2.lib.mixins import BaseCustomModelSerializer
from fin_app import models


class AllTimeGatewayModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.PayAllTimeGateway
        fields = '__all__'


class AllTimePayLogModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.AllTimePayLog
        fields = '__all__'
