from urllib.parse import urljoin

from django.db import models
from django.shortcuts import resolve_url
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.conf import settings
from viberbot import Api, BotConfiguration
from viberbot.api.messages import TextMessage
from viberbot.api.messages.message import Message
from messenger.models import Messenger


UserProfile = get_user_model()


class ViberMessenger(Messenger):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._viber_cache = None

    token = models.CharField(_('Bot secret token'), max_length=64)
    avatar = models.ImageField(_('Avatar'), upload_to='viber_avatar', null=True)

    def get_viber(self):
        if self._viber_cache is None:
            self._viber_cache = Api(BotConfiguration(
                name=str(self.slug),
                avatar=self.avatar.url,
                auth_token=str(self.token)
            ))
        return self._viber_cache

    def send_message_to_acc(self, to: UserProfile, msg):
        try:
            viber = self.get_viber()
            vs = to.vibersubscriber
            if issubclass(msg.__class__, Message):
                viber.send_messages(str(vs.uid), msg)
            else:
                viber.send_messages(str(vs.uid), TextMessage(text=msg))
        except ViberSubscriber.DoesNotExist:
            pass

    def send_message_to_accs(self, receivers, msg_text: str):
        """
        :param receivers: QuerySet of profiles.UserProfile
        :param msg_text: text message
        :return: nothing
        """
        viber = self.get_viber()
        msg = TextMessage(text=msg_text)
        for vs in ViberSubscriber.objects.filter(account__in=receivers).iterator():
            viber.send_messages(str(vs.uid), msg)

    def send_message_to_id(self, subscriber_id: str, msg):
        viber = self.get_viber()
        if issubclass(msg.__class__, Message):
            viber.send_messages(subscriber_id, msg)
        else:
            viber.send_messages(subscriber_id, TextMessage(text=msg))

    def send_webhook(self):
        pub_url = getattr(settings, 'VIBER_BOT_PUBLIC_URL')
        listen_url = resolve_url('messenger:listen_viber_bot', self.slug)
        public_url = urljoin(pub_url, listen_url)
        viber = self.get_viber()
        viber.set_webhook(public_url, ['failed', 'subscribed', 'unsubscribed', 'conversation_started'])

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'messenger_viber'
        verbose_name = _('Viber messenger')
        verbose_name_plural = _('Viber messengers')
        ordering = ('title',)


class ViberMessage(models.Model):
    msg = models.TextField(_('Message'))
    date = models.DateTimeField(
        _('Date'), auto_now_add=True
    )
    sender = models.CharField(
        _('Sender'), max_length=32
    )
    messenger = models.ForeignKey(
        ViberMessenger, verbose_name=_('Messenger'),
        on_delete=models.CASCADE
    )
    subscriber = models.ForeignKey(
        'ViberSubscriber', on_delete=models.SET_NULL,
        verbose_name=_('Subscriber'), null=True
    )

    def __str__(self):
        return self.msg

    class Meta:
        db_table = 'messenger_viber_messages'
        verbose_name = _('Viber message')
        verbose_name_plural = _('Viber messages')
        ordering = ('-date',)


class ViberSubscriber(models.Model):
    uid = models.CharField(
        _('User unique id in viber'),
        max_length=32
    )
    name = models.CharField(
        _('Name'), max_length=32,
        null=True, blank=True
    )
    avatar = models.URLField(
        _('Avatar'), max_length=250,
        null=True, blank=True
    )
    account = models.OneToOneField(
        UserProfile, on_delete=models.CASCADE,
        verbose_name=_('System account'),
        blank=True, null=True
    )

    def __str__(self):
        return self.name or 'no'

    class Meta:
        db_table = 'messenger_viber_subscriber'
        verbose_name = _('Viber subscriber')
        verbose_name_plural = _('Viber subscribers')
        ordering = ('name',)
