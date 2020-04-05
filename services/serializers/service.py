from rest_framework.serializers import (
    IntegerField, DateTimeField, CharField
)

from djing2.lib.mixins import BaseCustomModelSerializer
from services import models


class ServiceModelSerializer(BaseCustomModelSerializer):
    usercount = IntegerField(read_only=True)
    planned_deadline = DateTimeField(source='calc_deadline_formatted', read_only=True)
    calc_type_name = CharField(source='get_calc_type_display', read_only=True)

    class Meta:
        model = models.Service
        fields = (
            'pk', 'title', 'descr', 'speed_in', 'speed_out',
            'speed_burst', 'cost', 'calc_type', 'is_admin',
            'usercount', 'planned_deadline', 'calc_type_name'
        )


class PeriodicPayModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.PeriodicPay
        fields = (
            'pk', 'name', 'when_add',
            'amount'
        )


class OneShotPaySerializer(BaseCustomModelSerializer):
    pay_type_name = CharField(source='get_pay_type_display', read_only=True)

    class Meta:
        model = models.OneShotPay
        fields = '__all__'
