from urllib.parse import urljoin

from django.shortcuts import resolve_url
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from messenger.models.base_messenger import MessengerModel, MessengerSubscriberModel

from telebot import TeleBot, types


class TelegramMessengerModel(MessengerModel):
    avatar = models.ImageField(_("Avatar"), upload_to="telegram_avatar", null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        token = str(self.token)
        self.tlgrm = TeleBot(token)

    def set_webhook(self):
        pub_url = getattr(settings, "TELEGRAM_BOT_PUBLIC_URL")
        listen_url = resolve_url("messenger:listen_telegram_bot", self.slug)
        public_url = urljoin(pub_url, listen_url)
        self.tlgrm.set_webhook(url=public_url)

    def stop_webhook(self):
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

    def send_webhook(self):
        pub_url = getattr(settings, "TELEGRAM_BOT_PUBLIC_URL")
        listen_url = resolve_url("messenger:listen_telegram_bot", self.model.slug)
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
        # self.tlgrm.send_message(
        #     chat_id=2234234234,
        #     text=msg_text
        # )
        # for ts in MessengerSubscriber.objects.filter(account__in=receivers).iterator():
        #     ts.send_message(
        #         tb=self.tlgrm,
        #         text=msg_text
        #     )

    def send_message(self, msg_text: str):
        pass

    def inbox_data(self, data):
        # obj = self.get_object()

        upd = types.Update.de_json(data)
        # Incoming updates from telegram bot
        update_id = upd.update_id
        print("update_id", update_id)
        if upd.message is not None:
            print("Msg", upd.message)
            print("Msg text", upd.message.text)
        return "ok"

    class Meta:
        db_table = 'messengers_telegram'


MessengerModel.add_child_classes(
    messenger_type_name='telegram',
    unique_int=1,
    messenger_class=TelegramMessengerModel
)


class TelegramMessengerSubscriberModel(MessengerSubscriberModel):
    chat_id = models.CharField(_("User unique id in telegram"), max_length=32)

    def send_message(self, tb: TeleBot, msg_text: str):
        return tb.send_message(chat_id=self.chat_id, text=msg_text)

    def __str__(self):
        return self.name or "no"

    class Meta:
        db_table = "messengers_telegram_subscriber"
        verbose_name = _("Telegram subscriber")
        verbose_name_plural = _("Telegram subscribers")
        ordering = ("name",)
