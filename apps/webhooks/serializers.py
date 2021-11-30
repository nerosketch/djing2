from rest_framework.serializers import ModelSerializer
from webhooks.models import HookObserver


class HookObserverModelSerializer(ModelSerializer):
    class Meta:
        model = HookObserver
        fields = '__all__'
