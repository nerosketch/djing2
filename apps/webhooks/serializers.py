from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from webhooks.models import HookObserver, HookObserverNotificationTypes


class HookObserverModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = HookObserver
        fields = '__all__'
        exclude = ['user']


class ContentTypeSerializer(serializers.Serializer):
    app_label = serializers.CharField(max_length=100)
    model = serializers.CharField(max_length=100)


class HookObserverSubscribeSerializer(serializers.Serializer):
    notification_type = serializers.ChoiceField(
        choices=HookObserverNotificationTypes.choices
    )
    client_url = serializers.URLField()
    content_type = ContentTypeSerializer()


class ContentTypeModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentType
        fields = '__all__'
