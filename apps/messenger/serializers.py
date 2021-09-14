from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from djing2.lib.mixins import BaseCustomModelSerializer
from messenger.models import base_messenger as models


class MessengerModelSerializer(BaseCustomModelSerializer):
    bot_type_name = serializers.CharField(source='get_type_name', read_only=True)
    token = serializers.CharField(write_only=True)
    global_link = serializers.CharField(source='get_bot_url', read_only=True)
    current_webhook = serializers.CharField(source='get_webhook_url', read_only=True)

    def validate_bot_type(self, value):
        ints = tuple(int_class[0] for type_name, int_class in models.class_map.items())
        if value not in ints:
            raise serializers.ValidationError(_('"bot_type" not among the allowed values'))

        return value

    class Meta:
        model = models.MessengerModel
        fields = "__all__"


class MessengerSubscriberModelSerializer(BaseCustomModelSerializer):
    account_name = serializers.CharField(source="account.get_full_name", read_only=True)

    class Meta:
        model = models.MessengerSubscriberModel
        fields = "__all__"


class NotificationProfileOptionsModelSerializer(BaseCustomModelSerializer):
    class Meta:
        model = models.NotificationProfileOptionsModel
        fields = '__all__'
