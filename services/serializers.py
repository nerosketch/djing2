from rest_framework.serializers import (
    ModelSerializer, IntegerField,
    DateTimeField, CharField
)

from services import models


class ServiceModelSerializer(ModelSerializer):
    usercount = IntegerField(read_only=True)
    planned_deadline = DateTimeField(source='calc_deadline_formatted', read_only=True)
    calc_type_name = CharField(source='get_calc_type_display', read_only=True)

    class Meta:
        model = models.Service
        fields = (
            'pk', 'title', 'descr', 'speed_in', 'speed_out',
            'cost', 'calc_type', 'is_admin', 'usercount',
            'planned_deadline', 'calc_type_name'
        )


class PeriodicPayModelSerializer(ModelSerializer):
    class Meta:
        model = models.PeriodicPay
        fields = (
            'name', 'when_add',
            'calc_type', 'amount'
        )


class OneShotPaySerializer(ModelSerializer):
    class Meta:
        model = models.OneShotPay
        fields = '__all__'
