from rest_framework.serializers import ModelSerializer

from services.models import Service, PeriodicPay


class ServiceModelSerializer(ModelSerializer):
    class Meta:
        model = Service
        fields = (
            'pk', 'title', 'descr', 'speed_in', 'speed_out',
            'cost', 'calc_type', 'is_admin'
        )


class PeriodicPayModelSerializer(ModelSerializer):
    class Meta:
        model = PeriodicPay
        fields = (
            'name', 'when_add',
            'calc_type', 'amount'
        )
