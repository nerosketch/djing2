from rest_framework import serializers
from djing2.lib.mixins import BaseCustomModelSerializer
from fin_app.models.alltime import PayAllTimeGateway, AllTimePayLog


class AllTimeGatewayModelSerializer(BaseCustomModelSerializer):
    pay_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = PayAllTimeGateway
        fields = "__all__"


class PaysReportParamsSerializer(serializers.Serializer):
    from_date = serializers.DateTimeField()
    pay_gw = serializers.IntegerField(default=None, allow_null=True)
    group_by_day = serializers.NullBooleanField(default=False)
    group_by_mon = serializers.NullBooleanField(default=False)
    group_by_week = serializers.NullBooleanField(default=False)


class AllTimePayLogModelSerializer(BaseCustomModelSerializer):
    sum = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False, required=False)

    class Meta:
        model = AllTimePayLog
        fields = "__all__"


class PayAllTimeGatewayModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = PayAllTimeGateway
        fields = "__all__"
