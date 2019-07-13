from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model


UserProfile = get_user_model()


class Messenger(models.Model):
    title = models.CharField(_('Title'), max_length=64)
    CHAT_TYPES = (
        (1, _('Viber')),
    )
    bot_type = models.PositiveSmallIntegerField(_('Bot type'), choices=CHAT_TYPES, blank=True)
    slug = models.SlugField(_('Slug'))

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'messengers'
        verbose_name = _('Messenger')
        verbose_name_plural = _('Messengers')
        ordering = ('title',)
