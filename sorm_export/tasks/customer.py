from typing import List
from uwsgi_tasks import task
from customers.models import CustomerService
from sorm_export.hier_export.service import export_customer_service, export_customer_finish_service
from sorm_export.tasks.task_export import task_export


@task
def customer_service_export_task(customer_service_id_list: List[int], event_time=None):
    cservices = CustomerService.objects.filter(
        pk__in=customer_service_id_list
    )
    data, fname = export_customer_service(
        cservices=cservices,
        event_time=event_time
    )
    task_export(data, fname)


@task
def customer_service_finish_export_task(event_time=None, *args, **kwargs):
    data, fname = export_customer_finish_service(
        event_time=event_time,
        *args, **kwargs
    )
    task_export(data, fname)
