from typing import List
from uwsgi_tasks import task, TaskExecutor
from customers.models import CustomerService
from sorm_export.hier_export.service import export_customer_service
from sorm_export.tasks.task_export import task_export


@task(executir=TaskExecutor.SPOOLER)
def customer_service_export_task(customer_service_id_list: List[int], event_time=None):
    cservices = CustomerService.objects.filter(
        pk__in=customer_service_id_list
    )
    data, fname = export_customer_service(
        cservices=cservices,
        event_time=event_time
    )
    task_export(data, fname)
