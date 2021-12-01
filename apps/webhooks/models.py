from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType


class HookObserverNotificationTypes(models.IntegerChoices):
    UNKNOWN = 0
    MODEL_POST_SAVE = 1
    MODEL_POST_DELETE = 2
    MODEL_PRE_SAVE = 3
    MODEL_PRE_DELETE = 4


class HookObserver(models.Model):
    notification_type = models.PositiveSmallIntegerField(
        _('Notification type'),
        choices=HookObserverNotificationTypes.choices,
        default=HookObserverNotificationTypes.UNKNOWN
    )
    client_url = models.URLField(
        _('Client url')
    )
    content_type = models.ForeignKey(
        ContentType,
        models.CASCADE,
        verbose_name=_('content type'),
    )

    class Meta:
        db_table = 'hook_observer'
        unique_together = (
            'notification_type',
            'client_url',
            'content_type'
        )
