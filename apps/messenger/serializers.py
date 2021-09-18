from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from djing2.lib.mixins import BaseCustomModelSerializer
from djing2.serializers import BitFieldSerializer
from messenger.models import base_messenger as models
from messenger.models.base_messenger import notification_types


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


class NotificationFlagsBitFieldSerializer(BitFieldSerializer):
    def get_initial(self):
        flags = models.NotificationProfileOptionsModel.NOTIFICATION_FLAGS
        return ({
            'code': code,
            'label': label,
            'value': False
        } for code, label in flags)


class VariousOptionsSerializerField(serializers.JSONField):
    def get_initial(self):
        types = models.NotificationProfileOptionsModel.get_notification_types()
        return ({
            'code': code,
            'label': name,
            'value': False
        } for code, name in types.items())


class NotificationProfileOptionsModelSerializer(BaseCustomModelSerializer):
    notification_flags = NotificationFlagsBitFieldSerializer()
    various_options = VariousOptionsSerializerField()

    @staticmethod
    def validate_notification_flags(opts):
        available_flags = frozenset(models.NotificationProfileOptionsModel.get_all_options())
        flags = (getattr(models.NotificationProfileOptionsModel.notification_flags, code) for code, val in
                 opts if val and code in available_flags)
        fin_flags = 0
        for flag in flags:
            fin_flags = fin_flags | flag
        return fin_flags

    @staticmethod
    def validate_various_options(opts):
        available_opt_codes = {code for code, label in notification_types.items()}
        res = {code: True for code, val in opts if val and code in available_opt_codes}
        return res

    class Meta:
        model = models.NotificationProfileOptionsModel
        exclude = ['profile']
