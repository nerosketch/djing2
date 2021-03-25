from datetime import datetime

from uwsgi_tasks import task, cron

from djing2.lib import LogicError
from customers.models import Customer, PeriodicPayForId


@task()
def customer_check_service_for_expiration(customer_id: int):
    """
    Finish expired services and connect new services if enough money
    :param customer_id: customers.customer.Customer primary key
    :return: nothing
    """
    try:
        customer = Customer.objects.get(pk=customer_id)
        if customer.auto_renewal_service:
            if customer.current_service:
                Customer.objects.continue_services_if_autoconnect(
                    customer=customer
                )
            else:
                customer.connect_service_if_autoconnect()
        else:
            Customer.objects.finish_services_if_expired(
                customer=customer
            )

    except Customer.DoesNotExist:
        pass
    except LogicError as err:
        print(err)


def _manage_periodic_pays_run():
    now = datetime.now()
    ppays = PeriodicPayForId.objects.select_related('account', 'periodic_pay') \
        .filter(next_pay__lte=now, account__is_active=True)
    for pay in ppays.iterator():
        pay.payment_for_service(now=now)


def _manage_post_connect_services():
    customers = Customer.objects.filter(
        is_active=True,
        current_service=None,
        auto_renewal_service=True
    ).exclude(
        last_connected_service=None
    ).select_related('last_connected_service')
    for customer in customers.iterator():
        try:
            customer.connect_service_if_autoconnect()
        except LogicError:
            # TODO: May be log it?
            pass


@cron(minute=-33)
def manage_services(signal_number):
    now = datetime.now()
    with open('/tmp/manage_services.log', 'a') as f:
        f.write("%s: signal_number=%d\n" % (now, signal_number))

        Customer.objects.continue_services_if_autoconnect()
        Customer.objects.finish_services_if_expired()

        # Post connect service
        # connect service when autoconnect is True, and user have enough money
        _manage_post_connect_services()

        _manage_periodic_pays_run()

        f.write('%s: time delta=%s\n' % (datetime.now(), datetime.now() - now))
        f.write('#' * 20)
        f.write('\n')
