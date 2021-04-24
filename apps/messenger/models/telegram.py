from urllib.parse import urljoin

from django.shortcuts import resolve_url
from telebot import TeleBot
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from djing2.models import BaseAbstractModel
from messenger.models import Messenger
from profiles.models import UserProfile


class TelegramMessenger(Messenger):
    token = models.CharField(_("Bot secret token"), max_length=128)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        token = str(self.token)
        self.tlgrm = TeleBot(token)

    def set_webhook(self):
        pub_url = getattr(settings, "TELEGRAM_BOT_PUBLIC_URL")
        listen_url = resolve_url("messenger:listen_telegram_bot", self.slug)
        public_url = urljoin(pub_url, listen_url)
        self.tlgrm.set_webhook(url=public_url)

    def remove_webhook(self):
        self.tlgrm.remove_webhook()

    def send_message_to_accs(self, receivers, msg_text: str):
        """
        :param receivers: QuerySet of profiles.UserProfile
        :param msg_text: text message
        :return: nothing
        """
        self.tlgrm.send_message(chat_id=2234234234, text=msg_text)
        for ts in TelegramSubscriber.objects.filter(account__in=receivers).iterator():
            ts.send_message(tb=self.tlgrm, text=msg_text)


class TelegramSubscriber(BaseAbstractModel):
    chat_id = models.CharField(_("User unique id in telegram"), max_length=32)
    name = models.CharField(_("Name"), max_length=64, null=True, blank=True)
    account = models.OneToOneField(UserProfile, on_delete=models.CASCADE, verbose_name=_("System account"))

    def send_message(self, tb: TeleBot, msg_text: str):
        return tb.send_message(chat_id=self.chat_id, text=msg_text)

    def __str__(self):
        return self.name or "no"

    class Meta:
        db_table = "messenger_telegram_subscriber"
        verbose_name = _("Telegram subscriber")
        verbose_name_plural = _("Telegram subscribers")
        ordering = ("name",)
