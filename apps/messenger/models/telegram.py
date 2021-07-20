from django.db import models
from django.utils.translation import gettext_lazy as _

from messenger.models.base_messenger import MessengerModel, MessengerSubscriberModel

from telebot import TeleBot, types

TYPE_NAME = 'telegram'


class TelegramMessengerModel(MessengerModel):
    avatar = models.ImageField(_("Avatar"), upload_to="telegram_avatar", null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        token = str(self.token)
        self.tlgrm = TeleBot(token)

    def stop_webhook(self):
        self.tlgrm.remove_webhook()

    def send_webhook(self):
        public_url = self.get_webhook_url(type_name=TYPE_NAME)
        self.tlgrm.set_webhook(url=public_url)

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

    def inbox_data(self, request):
        # print('Inbox:', request.data)
        upd = types.Update.de_json(request.data)
        msg = upd.message
        # print('Msg:', msg)

        return self._reply_telephone_contact(
            button_text='Телефон из телеграма',
            chat_id=msg.chat.id,
            text='Нужен номер телефона из учётной записи в билинге'
        )

    @staticmethod
    def _reply_telephone_contact(button_text: str, chat_id: int, text: str):
        r = {
            'chat_id': str(chat_id),
            'text': text,
            'reply_markup': {
                'keyboard': [
                    [
                        {
                            'text': button_text,
                            'request_contact': True
                        }
                    ]
                ],
                'resize_keyboard': True,
                'one_time_keyboard': True
            },
            'method': 'sendMessage'
        }
        return r

    @staticmethod
    def _reply_text(chat_id: int, text: str, reply_to_msg_id=None):
        r = {
            'chat_id': chat_id,
            'text': text,
            'method': 'sendMessage'
        }
        if reply_to_msg_id is not None:
            r['reply_to_message_id'] = reply_to_msg_id
        return r

    class Meta:
        db_table = 'messengers_telegram'


MessengerModel.add_child_classes(
    messenger_type_name=TYPE_NAME,
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
