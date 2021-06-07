from datetime import datetime

from services.models import Service
from sorm_export.tasks.service import service_export_task
from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver


@receiver(post_save, sender=Service)
def service_post_save_signal(sender, instance: Service, created=False, **kwargs):
    service_export_task(
        service_id_list=[instance.pk],
        event_time=datetime.now()
    )
