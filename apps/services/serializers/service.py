from rest_framework.serializers import IntegerField, DateTimeField, CharField, DecimalField

from djing2.lib.mixins import BaseCustomModelSerializer
from services import models


class ServiceModelSerializer(BaseCustomModelSerializer):
    usercount = IntegerField(read_only=True)
    planned_deadline = DateTimeField(source="calc_deadline_formatted", read_only=True)
    calc_type_name = CharField(read_only=True)
    speed_in = DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False, required=False)
    speed_out = DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False, required=False)
    cost = DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False, required=False)

    class Meta:
        model = models.Service
        fields = (
            "pk",
            "title",
            "descr",
            "speed_in",
            "speed_out",
            "speed_burst",
            "cost",
            "calc_type",
            "is_admin",
            "usercount",
            "planned_deadline",
            "calc_type_name",
            "sites",
            "create_time",
        )


class PeriodicPayModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.PeriodicPay
        fields = ("pk", "name", "when_add", "amount", "sites")


class OneShotPaySerializer(BaseCustomModelSerializer):
    pay_type_name = CharField(source="get_pay_type_display", read_only=True)

    class Meta:
        model = models.OneShotPay
        fields = "__all__"
