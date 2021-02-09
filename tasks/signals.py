from django.utils.translation import gettext as _
from django.db.models.signals import post_save
from django.dispatch import receiver

from djing2.lib.ws_connector import send_data
from djing2.tasks import send_broadcast_push_notification
from tasks.models import Task


@receiver(post_save, sender=Task)
def task_post_save(sender, instance: Task, created=False, **kwargs):
    if instance.priority == Task.TASK_PRIORITY_HIGHER:
        notify_text = _('High priority task was created') if created else _('High priority task was updated')
        send_data({
            'eventType': 'updatetask',
            'text': notify_text,
            'data': {
                'recipients': list(instance.recipients.only('pk').values_list('pk', flat=True)),
                'author': instance.author_id if instance.author else None
            }
        })
        send_broadcast_push_notification(
            title=_('Reminders of tasks'),
            body=notify_text
        )
        return
    send_data({
        'eventType': 'updatetask'
    })
