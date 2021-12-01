from django.contrib.contenttypes.models import ContentType
from rest_framework.serializers import ModelSerializer
from webhooks.models import HookObserver


class HookObserverModelSerializer(ModelSerializer):
    class Meta:
        model = HookObserver
        fields = '__all__'


class ContentTypeModelSerializer(ModelSerializer):
    class Meta:
        model = ContentType
        fields = '__all__'
