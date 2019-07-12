from rest_framework import serializers
from messenger import models


class MessengerModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Messenger
        fields = '__all__'


class ViberMessengerModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ViberMessenger
        fields = '__all__'


class ViberMessageModelSerializer(serializers.ModelSerializer):
    subscriber_name = serializers.CharField(source='subscriber.get_full_name', read_only=True)

    class Meta:
        model = models.ViberMessage
        exclude = 'messenger',


class ViberSubscriberModelSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source='account.get_full_name', read_only=True)

    class Meta:
        model = models.ViberSubscriber
        fields = '__all__'
