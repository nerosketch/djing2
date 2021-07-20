from django.db import models
from django.utils.translation import gettext_lazy as _
from messenger.models.base_messenger import MessengerModel, MessengerSubscriberModel
from telebot import TeleBot, types
from profiles.models import UserProfile

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
        upd = types.Update.de_json(request.data)

        if upd.my_chat_member:
            mcm = upd.my_chat_member
            chat_id = mcm.chat.id
            if mcm.new_chat_member:
                st = mcm.new_chat_member.status
                if st == 'kicked':
                    # Kicked user from chat bot
                    return self._leave_chat_bot(
                        chat_id=chat_id
                    )
                elif st == 'member':
                    # create new subscriber
                    return self._make_subscriber(mcm.chat)
                else:
                    return None

        msg = upd.message
        if msg:
            text = msg.text
            if text == '/start':
                return self._reply_telephone_contact(
                    button_text=_('My telephone number'),
                    chat_id=msg.chat.id,
                    text=_('Telephone number required')
                )
            # handle_message_command(msg)
            if msg.contact:
                return self._inbox_contact(msg, msg.chat.id)

        return self._reply_text(
            chat_id=msg.chat.id,
            text=_()
        )

    @staticmethod
    def _reply_telephone_contact(button_text: str, chat_id: int, text: str):
        return {
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

    @classmethod
    def _inbox_contact(cls, msg: types.Message, chat_id: int):
        tel = msg.contact.phone_number
        accs = UserProfile.objects.filter(telephone__icontains=tel)
        if accs.exists():
            subs = TelegramMessengerSubscriberModel.objects.filter(
                chat_id=chat_id
            )
            subs_len = subs.count()
            if subs_len > 0:
                first_sub = subs.first()
                if subs_len > 1:
                    TelegramMessengerSubscriberModel.objects.exclude(pk=first_sub.pk).delete()
                first_sub.account = accs.first()
                first_sub.name = msg.from_user.full_name
                first_sub.save(update_fields=('account', 'name'))
                return cls._reply_text(
                    chat_id=chat_id,
                    text=_('Your account is attached. Now you will be receive notifications from billing')
                )
            else:
                return cls._reply_text(
                    chat_id=chat_id,
                    text=_('Subscription does not exists')
                )
        else:
            cls._reply_text(
                chat_id=chat_id,
                text=_('Telephone not found, please specify telephone number in account in billing')
            )

    @staticmethod
    def _make_subscriber(chat: types.Chat):
        TelegramMessengerSubscriberModel.objects.get_or_create(
            chat_id=chat.id,
            defaults={
                'name': "%s %s" % (chat.first_name, chat.last_name),
            }
        )

    @classmethod
    def _leave_chat_bot(cls, chat_id: int):
        TelegramMessengerSubscriberModel.objects.filter(
            chat_id=chat_id
        ).delete()

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
