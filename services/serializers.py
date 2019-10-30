from rest_framework.serializers import ModelSerializer, IntegerField, DateTimeField

from services.models import Service, PeriodicPay


class ServiceModelSerializer(ModelSerializer):
    usercount = IntegerField(read_only=True)
    planned_deadline = DateTimeField(source='calc_deadline_formatted', read_only=True)

    class Meta:
        model = Service
        fields = (
            'pk', 'title', 'descr', 'speed_in', 'speed_out',
            'cost', 'calc_type', 'is_admin', 'usercount',
            'planned_deadline'
        )


class PeriodicPayModelSerializer(ModelSerializer):
    class Meta:
        model = PeriodicPay
        fields = (
            'name', 'when_add',
            'calc_type', 'amount'
        )
