from .base import BaseMessengerInterface
from urllib.parse import urljoin

from django.shortcuts import resolve_url
from telebot import TeleBot
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class TelegramMessenger(BaseMessengerInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        token = str(self.token)
        self.tlgrm = TeleBot(token)

    def send_webhook(self):
        pub_url = getattr(settings, 'TELEGRAM_BOT_PUBLIC_URL')
        listen_url = resolve_url('messenger:listen_telegram_bot', self.slug)
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

        upd = types.Update.de_json(request.data)
        # Incoming updates from telegram bot
        update_id = upd.update_id
        print('update_id', update_id)
        if upd.message is not None:
            print('Msg', upd.message)
            print('Msg text', upd.message.text)
        return 'ok'
