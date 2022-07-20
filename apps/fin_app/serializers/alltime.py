from rest_framework import serializers
from djing2.lib.mixins import BaseCustomModelSerializer
from fin_app.models.alltime import AllTimePayGateway, AllTimePaymentLog


class AllTimeGatewayModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = AllTimePayGateway
        fields = "__all__"


class AllTimePayLogModelSerializer(BaseCustomModelSerializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False, required=False)

    class Meta:
        model = AllTimePaymentLog
        fields = "__all__"


class PayAllTimeGatewayModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = AllTimePayGateway
        fields = "__all__"
