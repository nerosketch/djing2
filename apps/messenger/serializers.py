from rest_framework import serializers

from djing2.lib.mixins import BaseCustomModelSerializer
from messenger.models import messenger as models


class MessengerModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.MessengerModel
        fields = "__all__"


class MessengerSubscriberModelSerializer(BaseCustomModelSerializer):
    account_name = serializers.CharField(source="account.get_full_name", read_only=True)

    class Meta:
        model = models.MessengerSubscriberModel
        fields = "__all__"
