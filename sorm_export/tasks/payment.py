from typing import List

from uwsgi_tasks import task, TaskExecutor

from fin_app.models import AllTimePayLog
from sorm_export.hier_export.payment import export_customer_unknown_payment
from sorm_export.tasks.task_export import task_export


@task(executir=TaskExecutor.SPOOLER)
def export_customer_payment_task(pay_log_id_list: List[int], event_time=None):
    leases = AllTimePayLog.objects.filter(
        pk__in=pay_log_id_list
    )
    data, fname = export_customer_unknown_payment(
        leases=leases,
        event_time=event_time
    )
    task_export(data, fname)
