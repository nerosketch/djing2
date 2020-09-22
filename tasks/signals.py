from django.db.models.signals import post_save
from django.dispatch import receiver

from djing2.lib.ws_connector import send_data
from tasks.models import Task


@receiver(post_save, sender=Task)
def task_post_save(sender, **kwargs):
    send_data({
        'eventType': 'updatetask',
        'data': None
    })
