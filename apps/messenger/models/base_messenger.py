import abc
from django.db import models
from django.utils.translation import gettext_lazy as _

from djing2.models import BaseAbstractModel
from profiles.models import UserProfile


# class MessengerBotType(models.IntegerChoices):
#     VIBER = 1, _("Viber")
#     TELEGRAM = 2, _("Telegram")


class MessengerModel(BaseAbstractModel):
    title = models.CharField(_("Title"), max_length=64)
    description = models.TextField(_("Description"), null=True, blank=True, default=None)
    # bot_type = models.PositiveSmallIntegerField(_("Bot type"), choices=MessengerBotType.choices, blank=True)
    token = models.CharField(_("Bot secret token"), max_length=128)

    class_map = {}

    @classmethod
    def add_child_classes(cls, messenger_type_name: str, messenger_class):
        cls.class_map[messenger_type_name] = messenger_class

    @abc.abstractmethod
    def send_webhook(self, request):
        pass

    @abc.abstractmethod
    def stop_webhook(self, request):
        pass

    @abc.abstractmethod
    def inbox_data(self, request):
        pass

    def __str__(self):
        return self.title

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

    def __str__(self):
        return self.name or "no"

    class Meta:
        db_table = "messenger_subscriber"
        verbose_name = _("Subscriber")
        verbose_name_plural = _("Subscribers")
        ordering = ("name",)
