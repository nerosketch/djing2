import csv
from io import StringIO
from typing import List

from uwsgi_tasks import task, TaskExecutor

from customers.models import CustomerService
from sorm_export.ftp_worker.func import send_text_file
from sorm_export.hier_export.service import export_customer_service


class Conv2BinStringIO(StringIO):
    def readline(self, *args, **kwargs):
        r = super().readline(*args, **kwargs)
        if isinstance(r, str):
            return r.encode()
        return r


# customer_service_id_list = [2265, 2266, 2324, 2326, 2394, 2574, 3034, 3035, 3294, 3297, 3301, 3307, 3308, 3309, 3310]
@task(executir=TaskExecutor.SPOOLER)
def customer_service_export_task(customer_service_id_list: List[int]):
    cservices = CustomerService.objects.filter(
        pk__in=customer_service_id_list
    )
    data, fname = export_customer_service(
        cservices=cservices
    )
    csv_buffer = Conv2BinStringIO()
    csv_writer = csv.writer(csv_buffer, dialect='unix')
    for row_data in data:
        row = (eld for elt, eld in row_data.items())
        csv_writer.writerow(row)
    csv_buffer.seek(0)

    send_text_file(csv_buffer, fname)
