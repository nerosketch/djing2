from rest_framework import serializers
from djing2.lib.mixins import BaseCustomModelSerializer
from fin_app.models.base_payment_model import BasePaymentModel, BasePaymentLogModel


class PaysReportParamsSerializer(serializers.Serializer):
    from_time = serializers.DateTimeField()
    to_time = serializers.DateTimeField()
    pay_gw = serializers.IntegerField(default=None, allow_null=True)
    group_by = serializers.IntegerField(default=0)
    limit = serializers.IntegerField(default=50)


class BasePaymentModelSerializer(BaseCustomModelSerializer):
    pay_count = serializers.IntegerField(read_only=True)
    payment_type_text = serializers.CharField(source='get_payment_type_display', read_only=True)

    class Meta:
        model = BasePaymentModel
        fields = "__all__"


class BasePaymentLogModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = BasePaymentLogModel
        fields = "__all__"
