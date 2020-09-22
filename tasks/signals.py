from django.utils.translation import gettext as _
from django.db.models.signals import post_save
from django.dispatch import receiver

from djing2.lib.ws_connector import send_data
from tasks.models import Task


@receiver(post_save, sender=Task)
def task_post_save(sender, instance: Task, created=False, **kwargs):
    if instance.priority == Task.TASK_PRIORITY_HIGHER:
        send_data({
            'eventType': 'updatetask',
            'text': _('High priority task was created') if created else _('High priority task was updated'),
            'data': {
                'recipients': list(instance.recipients.only('pk').values_list('pk', flat=True)),
            }
        })
        return
    send_data({
        'eventType': 'updatetask'
    })
