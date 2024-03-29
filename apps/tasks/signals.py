from django.utils.translation import gettext as _
from django.db.models.signals import post_save
from django.dispatch import receiver

from djing2.lib.ws_connector import send_data2ws, WsEventTypeEnum
from tasks.models import Task, TaskPriorities


@receiver(post_save, sender=Task)
def task_post_save(sender, instance: Task, created=False, **kwargs):
    if instance.priority == TaskPriorities.TASK_PRIORITY_HIGHER:
        if created:
            notify_title = _("High priority task was created")
        else:
            notify_title = _("High priority task was updated")
        recipients = instance.recipients.only("pk").values_list("pk", flat=True)
        send_data2ws(
            {
                "eventType": WsEventTypeEnum.UPDATE_TASK.value,
                "text": notify_title,
                "data": {
                    "recipients": list(recipients),
                    "author": instance.author_id if instance.author else None,
                    "task_id": instance.pk,
                },
            }
        )
        # FIXME: hardcode url
        # notify_text = "{customer_name}: {text}".format(
        #     customer_name=instance.customer.get_full_name(),
        #     text=instance.descr,
        # )
        # TODO: enable push
        # send_broadcast_push_notification(title=notify_title, body=notify_text, url=f"/tasks/t{instance.pk}")
        return
    send_data2ws({"eventType": WsEventTypeEnum.UPDATE_TASK.value, "data": {"task_id": instance.pk}})
