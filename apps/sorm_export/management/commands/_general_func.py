from django.db.models import Count

from customers.models import Customer
from networks.models import CustomerIpLeaseModel
from sorm_export.ftp_worker.func import send_text_buf2ftp
from sorm_export.tasks.task_export import Conv2BinStringIO


def export_customer_lease_binds():
    def _exp():
        customers = Customer.objects.annotate(leasecount=Count("customeripleasemodel")).filter(
            is_active=True, leasecount__gt=0
        )
        for customer in customers.iterator():
            ips = (lease.ip_address for lease in CustomerIpLeaseModel.objects.filter(customer=customer))
            ips = ",".join(ips)
            yield f"{customer.username};{ips}"

    fname = "customer_ip_binds.txt"
    csv_buffer = Conv2BinStringIO()
    for row_data in _exp():
        csv_buffer.write("%s\n" % row_data)
    csv_buffer.seek(0)
    send_text_buf2ftp(csv_buffer, fname)
