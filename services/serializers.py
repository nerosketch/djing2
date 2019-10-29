from rest_framework.serializers import ModelSerializer, IntegerField

from services.models import Service, PeriodicPay


class ServiceModelSerializer(ModelSerializer):
    usercount = IntegerField(read_only=True)

    class Meta:
        model = Service
        fields = (
            'pk', 'title', 'descr', 'speed_in', 'speed_out',
            'cost', 'calc_type', 'is_admin', 'usercount'
        )


class PeriodicPayModelSerializer(ModelSerializer):
    class Meta:
        model = PeriodicPay
        fields = (
            'name', 'when_add',
            'calc_type', 'amount'
        )
