import csv
from uwsgi_tasks import cron, TaskExecutor
from django.conf import settings
from django.db.models import Count
from django.core.mail import EmailMessage
from customers.models import Customer
from io import StringIO


# @task(executor=TaskExecutor.SPOOLER)
@cron(minute=13, hour=0, executor=TaskExecutor.SPOOLER)
def report_customer_without_contracts_task(signal_number):
    sorm_reporting_emails = getattr(settings, 'SORM_REPORTING_EMAILS', None)
    if not sorm_reporting_emails:
        return

    customers = Customer.objects.annotate(
        ccc=Count('customercontractmodel')
    ).filter(
        ccc=0,
        is_active=True
    )
    csv_buffer = StringIO()

    writer = csv.DictWriter(csv_buffer, fieldnames=['id', 'логин', 'фио'])
    writer.writeheader()
    for customer in customers.iterator():
        vals = {
            'id': customer.pk,
            'логин': customer.username,
            'фио': customer.get_full_name()
        }
        writer.writerow(vals)
    # csv_buffer.seek(0)

    email = EmailMessage(
        'Абоненты без договоров',
        'Количество: %d\n%s' % (customers.count(), csv_buffer.getvalue()),
        getattr(settings, 'DEFAULT_FROM_EMAIL'),
        sorm_reporting_emails
    )
    # print(csv_buffer.getvalue())
    email.attach('Абоненты без договоров.csv', csv_buffer.getvalue(), 'text/csv')
    email.send()
