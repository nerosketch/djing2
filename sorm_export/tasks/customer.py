from typing import List
from uwsgi_tasks import task
from customers.models import CustomerService
from sorm_export.hier_export.customer import export_contact
from sorm_export.hier_export.service import export_customer_service, export_manual_data_customer_service
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
def customer_service_manual_data_export_task(event_time=None, *args, **kwargs):
    data, fname = export_manual_data_customer_service(
        event_time=event_time,
        *args, **kwargs
    )
    task_export(data, fname)


@task
def customer_contact_export_task(customer_tels, event_time=None):
    data, fname = export_contact(
        customer_tels=customer_tels,
        event_time=event_time
    )
    task_export(data, fname)
