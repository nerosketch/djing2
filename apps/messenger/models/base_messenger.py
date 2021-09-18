import abc
from typing import Optional, Tuple, Generator
from urllib.parse import urljoin

from django.shortcuts import resolve_url
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import gettext_lazy as _
from bitfield import BitField

from djing2.models import BaseAbstractModel
from profiles.models import UserProfile


class_map = {}


#
# Stores notification types
# For example:
# notification_types = {
#     'task': _('Notify about tasks'),
#     'device': _('Notify about device events'),
# }
#
notification_types = {}


def get_messenger_model_by_name(name: str) -> Optional[ModelBase]:
    uint, model_class = class_map.get(name, None)
    return model_class


def get_messenger_model_by_uint(uint: int) -> Optional[ModelBase]:
    fg = (int_class[1] for type_name, int_class in class_map.items() if int_class[0] == uint)
    return next(fg, None)


def get_messenger_model_info_generator() -> Generator[Tuple[str, int, ModelBase], None, None]:
    return ((type_name, int_class[0], int_class[1]) for type_name, int_class in class_map.items())


class MessengerModel(BaseAbstractModel):
    title = models.CharField(_("Title"), max_length=64)
    description = models.TextField(_("Description"), null=True, blank=True, default=None)
    bot_type = models.PositiveSmallIntegerField(
        _("Bot type")
    )
    token = models.CharField(_("Bot secret token"), max_length=128)

    @staticmethod
    def add_child_classes(messenger_type_name: str, unique_int: int, messenger_class):
        """
        Stores implemented class and its associated data.
        :param messenger_type_name: string latin name of messenger type.
                                    'viber' or 'telegram' for example
        :param unique_int: int number that stores in db, and participants
                            in choices parameter for messenger type
        :param messenger_class: Child of MessengerModel class
        """
        global class_map
        r = (int_class_tuple[0] for _, int_class_tuple in class_map.items() if int_class_tuple[0] == unique_int)
        if next(r, None) is not None:
            raise ImproperlyConfigured('Your unique_int already busy, choose some another number')

        class_map[messenger_type_name] = (unique_int, messenger_class)

    @abc.abstractmethod
    def send_webhook(self):
        raise NotImplementedError

    @abc.abstractmethod
    def stop_webhook(self):
        raise NotImplementedError

    @abc.abstractmethod
    def inbox_data(self, request):
        raise NotImplementedError

    @abc.abstractmethod
    def send_message_to_acc(self, to: UserProfile, msg: str):
        raise NotImplementedError

    @abc.abstractmethod
    def send_message(self, text: str, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def send_message_broadcast(self, text: str, profile_ids=None):
        """
        :param text: Message text.
        :param profile_ids: list of profiles.UserProfile.id, optional.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_bot_url(self):
        raise NotImplementedError

    def get_webhook_url(self):
        type_name = self.get_type_name()
        pub_url = getattr(settings, "MESSENGER_BOT_PUBLIC_URL")
        listen_url = resolve_url(f"messenger:messenger-{type_name}-listen-bot", pk=self.pk)
        public_url = urljoin(pub_url, listen_url)
        return public_url

    def __str__(self):
        return self.title

    def get_type_name(self) -> Optional[str]:
        uint = int(self.bot_type)
        g = (type_name for type_name, int_class in class_map.items() if int_class[0] == uint)
        return next(g, None)

    class Meta:
        db_table = "messengers"
        verbose_name = _("Messenger")
        verbose_name_plural = _("Messengers")
        ordering = ("title",)


class MessengerSubscriberModel(BaseAbstractModel):
    name = models.CharField(_("Name"), max_length=32, null=True, blank=True)
    avatar = models.URLField(_("Avatar"), max_length=250, null=True, blank=True)
    account = models.OneToOneField(
        UserProfile, on_delete=models.CASCADE, verbose_name=_("System account"), blank=True, null=True
    )

    def send_message(self, msg_text: str):
        pass

    def __str__(self):
        return self.name or "no"

    class Meta:
        db_table = "messenger_subscriber"
        verbose_name = _("Subscriber")
        verbose_name_plural = _("Subscribers")
        ordering = ("name",)


class NotificationProfileOptionsModel(models.Model):
    profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    NOTIFICATION_TELEGRAM_FLAG = 'telegram'
    NOTIFICATION_VIBER_FLAG = 'viber'
    NOTIFICATION_EMAIL_FLAG = 'email'
    NOTIFICATION_PUSH_FLAG = 'push'
    NOTIFICATION_CUSTOM_FLAG = 'custom'
    NOTIFICATION_FLAGS = (
        (NOTIFICATION_TELEGRAM_FLAG, _('Telegram notifications')),
        (NOTIFICATION_VIBER_FLAG, _('Viber notifications')),
        (NOTIFICATION_EMAIL_FLAG, _('Email notifications')),
        (NOTIFICATION_PUSH_FLAG, _('Push notifications')),
        (NOTIFICATION_CUSTOM_FLAG, _('Custom notifications')),
    )
    notification_flags = BitField(flags=NOTIFICATION_FLAGS, default=0)
    various_options = models.JSONField()

    @staticmethod
    def get_all_options():
        available_flags = (flag_code for flag_code, flag_description in
                           NotificationProfileOptionsModel.NOTIFICATION_FLAGS)
        return available_flags

    @staticmethod
    def get_notification_types():
        return notification_types

    @staticmethod
    def add_notification_type(code: str, label: str):
        global notification_types
        if notification_types.get(code) is not None:
            raise ValueError('Notification type code "%s" already exists' % code)
        notification_types[code] = label

    class Meta:
        db_table = 'messenger_options'
