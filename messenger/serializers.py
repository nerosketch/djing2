from rest_framework import serializers

from djing2.lib.mixins import BaseCustomModelSerializer
from messenger import models


class MessengerModelSerializer(BaseCustomModelSerializer):
    bot_type_name = serializers.CharField(source='get_bot_type_display', read_only=True)

    class Meta:
        model = models.Messenger
        fields = '__all__'


class MessengerMessageModelSerializer(BaseCustomModelSerializer):
    subscriber_name = serializers.CharField(source='subscriber.get_full_name', read_only=True)

    class Meta:
        model = models.MessengerMessage
        exclude = 'messenger',


class MessengerSubscriberModelSerializer(BaseCustomModelSerializer):
    account_name = serializers.CharField(source='account.get_full_name', read_only=True)

    class Meta:
        model = models.MessengerSubscriber
        fields = '__all__'
