from typing import List

from uwsgi_tasks import task

from networks.models import CustomerIpLeaseModel
from sorm_export.hier_export.networks import export_ip_leases
from sorm_export.models import ExportStampTypeEnum
from sorm_export.tasks.task_export import task_export


@task
def export_ip_leases_task(customer_lease_id_list: List[int], event_time=None):
    leases = CustomerIpLeaseModel.objects.filter(
        pk__in=customer_lease_id_list
    )
    data, fname = export_ip_leases(
        leases=leases,
        event_time=event_time
    )
    task_export(data, fname, ExportStampTypeEnum.NETWORK_STATIC_IP)
