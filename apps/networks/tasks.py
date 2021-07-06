from datetime import datetime, timedelta
from uwsgi_tasks import cron
from networks.models import CustomerIpLeaseModel


@cron(minute=-30)
def periolicly_checks_for_stale_leases(signal_number):
    CustomerIpLeaseModel.objects.filter(last_update__lte=datetime.now() - timedelta(days=2), is_dynamic=True).delete()
