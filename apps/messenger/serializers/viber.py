from rest_framework import serializers

from djing2.lib.mixins import BaseCustomModelSerializer
from messenger.models import viber as models


class ViberMessengerModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.ViberMessenger
        fields = "__all__"


class ViberMessageModelSerializer(BaseCustomModelSerializer):
    subscriber_name = serializers.CharField(source="subscriber.get_full_name", read_only=True)

    class Meta:
        model = models.ViberMessage
        exclude = ("messenger",)


class ViberSubscriberModelSerializer(BaseCustomModelSerializer):
    account_name = serializers.CharField(source="account.get_full_name", read_only=True)

    class Meta:
        model = models.ViberSubscriber
        fields = "__all__"
