from typing import List
from djing2 import celery_app
from customers.models import CustomerService
from sorm_export.hier_export.service import ManualDataCustomerServiceSimpleExportTree, CustomerServiceExportTree
from sorm_export.hier_export.customer import ContactSimpleExportTree


@celery_app.task
def customer_service_export_task(customer_service_id_list: List[int], event_time=None):
    cservices = CustomerService.objects.filter(
        pk__in=customer_service_id_list
    )
    CustomerServiceExportTree(event_time=event_time).exportNupload(queryset=cservices)


@celery_app.task
def customer_service_manual_data_export_task(event_time=None, *args, **kwargs):
    ManualDataCustomerServiceSimpleExportTree(event_time=event_time).exportNupload(*args, **kwargs)


@celery_app.task
def customer_contact_export_task(customer_tels, event_time=None):
    ContactSimpleExportTree(event_time=event_time).exportNupload(data=customer_tels, many=True)


#@celery_app.task
#def customer_root_export_task(customer_id: int, event_time=None):
#    exporter = CustomerRootExportTree(recursive=False)
#    data, fname = export_customer_root(
#        customers=Customer.objects.filter(pk=customer_id),
#        event_time=event_time
#    )
#    task_export(data, fname)
