from django.db import models
from django.utils.translation import gettext_lazy as _


class MessengerBotType(models.IntegerChoices):
    VIBER = 1, _('Viber')


class Messenger(models.Model):
    title = models.CharField(_('Title'), max_length=64)
    bot_type = models.PositiveSmallIntegerField(_('Bot type'), choices=MessengerBotType.choices, blank=True)
    slug = models.SlugField(_('Slug'))

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'messengers'
        verbose_name = _('Messenger')
        verbose_name_plural = _('Messengers')
        ordering = ('title',)
