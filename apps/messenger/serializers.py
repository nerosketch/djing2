from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from bitfield.models import BitHandler

from djing2.lib.mixins import BaseCustomModelSerializer
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


class NotificationFlagsBitFieldSerializer(serializers.Field):
    def to_representation(self, value: BitHandler):
        if isinstance(value, BitHandler):
            return ({
                'code': code,
                'label': value.get_label(code),
                'value': val
            } for code, val in value)
        return value

    def to_internal_value(self, opts):
        available_flags = frozenset(models.NotificationProfileOptionsModel.get_all_options())
        flags = (getattr(models.NotificationProfileOptionsModel.notification_flags, opt.get('code')) for opt in
                 opts if opt.get('value', False) and opt.get('code') in available_flags)
        fin_flags = 0
        for flag in flags:
            fin_flags = fin_flags | flag
        return fin_flags


class VariousOptionsSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=64)
    label = serializers.CharField(max_length=64)
    value = serializers.BooleanField(default=False)


class NotificationProfileOptionsModelSerializer(BaseCustomModelSerializer):
    notification_flags = NotificationFlagsBitFieldSerializer()
    various_options = VariousOptionsSerializer(many=True)

    @classmethod
    def _get_various_options_initial(cls):
        types = models.NotificationProfileOptionsModel.get_notification_types()
        return ({
            'code': code,
            'label': name,
            'value': False
        } for code, name in types.items())

    @classmethod
    def get_notification_flags_initial(cls):
        flags = models.NotificationProfileOptionsModel.NOTIFICATION_FLAGS
        return ({
            'code': code,
            'label': label,
            'value': False
        } for code, label in flags)

    def get_initial(self):
        return {
            'various_options': self._get_various_options_initial(),
            'notification_flags': self.get_notification_flags_initial()
        }

    @staticmethod
    def validate_various_options(opts):
        available_opt_codes = {code for code, label in notification_types.items()}
        for opt in opts:
            if opt.get('code') not in available_opt_codes:
                raise serializers.ValidationError("various_options has invalid code", code='invalid')
        return opts

    class Meta:
        model = models.NotificationProfileOptionsModel
        exclude = ['profile']
