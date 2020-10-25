from django.db import models
from django.utils.translation import gettext_lazy as _
from messenger.messenger_implementation import MESSENGER_MAP
from djing2.models import BaseAbstractModel
from profiles.models import UserProfile


_MESSENGER_CHOICES = ((m_num, m_obj.description) for m_num, m_obj in MESSENGER_MAP.items())


class Messenger(BaseAbstractModel):
    title = models.CharField(_('Title'), max_length=64)
    description = models.TextField(_('Description'), null=True, blank=True, default=None)
    bot_type = models.PositiveSmallIntegerField(_('Bot type'), choices=_MESSENGER_CHOICES, blank=True)
    slug = models.SlugField(_('Slug'))
    token = models.CharField(_('Bot secret token'), max_length=128)
    avatar = models.ImageField(_('Avatar'), upload_to='messenger_avatar', null=True)

    def inbox_data(self, request):
        bot_type_class = MESSENGER_MAP.get(self.bot_type)
        if bot_type_class is None:
            return
        bot_type_instance = bot_type_class(
            model=self,
            request=request
        )
        return bot_type_instance.inbox_data(request.data)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'messengers'
        verbose_name = _('Messenger')
        verbose_name_plural = _('Messengers')
        ordering = 'title',


class MessengerMessage(BaseAbstractModel):
    msg = models.TextField(_('Message'))
    date = models.DateTimeField(
        _('Date'), auto_now_add=True
    )
    sender = models.CharField(
        _('Sender'), max_length=32
    )
    messenger = models.ForeignKey(
        Messenger, verbose_name=_('Messenger'),
        on_delete=models.CASCADE
    )
    subscriber = models.ForeignKey(
        'MessengerSubscriber', on_delete=models.SET_NULL,
        verbose_name=_('Subscriber'), null=True
    )

    def __str__(self):
        return self.msg

    class Meta:
        db_table = 'messenger_messages'
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')
        ordering = '-date',


class MessengerSubscriber(BaseAbstractModel):
    uid = models.CharField(
        _('User unique id'),
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
        db_table = 'messenger_subscriber'
        verbose_name = _('Subscriber')
        verbose_name_plural = _('Subscribers')
        ordering = 'name',
