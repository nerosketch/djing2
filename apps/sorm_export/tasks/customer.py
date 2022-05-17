from typing import List
from uwsgi_tasks import task
from customers.models import CustomerService
from sorm_export.hier_export.service import ManualDataCustomerServiceSimpleExportTree, CustomerServiceExportTree
from sorm_export.hier_export.customer import ContactSimpleExportTree
from sorm_export.models import ExportStampTypeEnum


@task()
def customer_service_export_task(customer_service_id_list: List[int], event_time=None):
    cservices = CustomerService.objects.filter(
        pk__in=customer_service_id_list
    )
    exporter = CustomerServiceExportTree(event_time=event_time)
    data = exporter.export(queryset=cservices)
    exporter.upload2ftp(data=data, export_type=ExportStampTypeEnum.SERVICE_CUSTOMER)


@task()
def customer_service_manual_data_export_task(event_time=None, *args, **kwargs):
    exporter = ManualDataCustomerServiceSimpleExportTree(event_time=event_time)
    data = exporter.export(*args, **kwargs)
    exporter.upload2ftp(data=data, export_type=ExportStampTypeEnum.SERVICE_CUSTOMER_MANUAL)


@task()
def customer_contact_export_task(customer_tels, event_time=None):
    exporter = ContactSimpleExportTree(event_time=event_time)
    data = exporter.export(data=customer_tels, many=True)
    exporter.upload2ftp(data=data, export_type=ExportStampTypeEnum.CUSTOMER_CONTACT)


#@task()
#def customer_root_export_task(customer_id: int, event_time=None):
#    exporter = CustomerRootExportTree(recursive=False)
#    data, fname = export_customer_root(
#        customers=Customer.objects.filter(pk=customer_id),
#        event_time=event_time
#    )
#    task_export(data, fname, ExportStampTypeEnum.CUSTOMER_ROOT)
