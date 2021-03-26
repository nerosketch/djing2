from django.utils.translation import gettext as _
from django.db.models.signals import post_save
from django.dispatch import receiver

from djing2.lib.ws_connector import send_data2ws, WsEventTypeEnum
from djing2.tasks import send_broadcast_push_notification
from tasks.models import Task


@receiver(post_save, sender=Task)
def task_post_save(sender, instance: Task, created=False, **kwargs):
    if instance.priority == Task.TASK_PRIORITY_HIGHER:
        if created:
            notify_text = _("High priority task was created")
        else:
            notify_text = _("High priority task was updated")
        recipients = instance.recipients.only("pk").values_list("pk", flat=True)
        send_data2ws(
            {
                "eventType": WsEventTypeEnum.UPDATE_TASK.value,
                "text": notify_text,
                "data": {"recipients": list(recipients), "author": instance.author_id if instance.author else None},
            }
        )
        send_broadcast_push_notification(title=_("Reminders of tasks"), body=notify_text)
        return
    send_data2ws({"eventType": WsEventTypeEnum.UPDATE_TASK.value})
