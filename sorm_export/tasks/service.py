from typing import List
from uwsgi_tasks import task
from services.models import Service
from sorm_export.hier_export.service import export_nomenclature
from sorm_export.tasks.task_export import task_export


@task
def service_export_task(service_id_list: List[int], event_time=None):
    services = Service.objects.filter(
        pk__in=service_id_list
    )
    data, fname = export_nomenclature(
        services=services,
        event_time=event_time
    )
    task_export(data, fname)
