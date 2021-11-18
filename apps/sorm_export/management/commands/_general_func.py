from itertools import groupby

from networks.models import CustomerIpLeaseModel
from sorm_export.ftp_worker.func import send_text_buf2ftp
from sorm_export.tasks.task_export import Conv2BinStringIO


def export_customer_lease_binds():
    def _exp():
        leases = CustomerIpLeaseModel.objects.filter(customer__is_active=True)\
            .select_related('customer')\
            .order_by('customer__username')\
            .iterator()
        lease_groups = groupby(leases, key=lambda l: l.customer.username)
        for uname, lease_group in lease_groups:
            ips = ','.join(lease.ip_address for lease in lease_group)
            yield f"{uname};{ips}"

    fname = "customer_ip_binds.txt"
    csv_buffer = Conv2BinStringIO()
    for row_data in _exp():
        csv_buffer.write("%s\n" % row_data)
    csv_buffer.seek(0)
    send_text_buf2ftp(csv_buffer, fname)
