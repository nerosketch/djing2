#!/usr/bin/env python3
import os
from threading import Thread
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "djing.settings")
django.setup()
from django.utils import timezone
from django.db import transaction
from django.db.models import Count
from customers.models import Customer, CustomerService, PeriodicPayForId, CustomerLog
from gateways.nas_managers import GatewayNetworkError, GatewayFailedResult
from gateways.models import Gateway
from djing2.lib import LogicError


class NasSyncThread(Thread):
    def __init__(self, gw):
        super(NasSyncThread, self).__init__()
        self.gw = gw

    def run(self):
        try:
            tm = self.gw.get_gw_manager()
            users = Customer.objects \
                .filter(is_active=True, gateway=self.gw) \
                .exclude(current_service=None, ip_address=None) \
                .iterator()
            tm.sync_nas(users)
        except GatewayNetworkError as er:
            print('NetworkTrouble:', er)
        except Gateway.DoesNotExist:
            raise NotImplementedError


def main():
    CustomerService.objects.filter(customer=None).delete()
    now = timezone.now()
    fields = ('id', 'service__title', 'customer__id', 'customer__username')
    expired_services = CustomerService.objects.exclude(customer=None).filter(
        deadline__lt=now,
        customer__auto_renewal_service=False
    )

    # finishing expires services
    with transaction.atomic():
        for ex_srv in expired_services.only(*fields).values(*fields):
            log = CustomerLog.objects.create(
                customer_id=ex_srv['customer__id'],
                cost=0,
                author=None,
                date=now,
                comment="Срок действия услуги '%(service_name)s' для '%(username)s' истёк" % {
                    'service_name': ex_srv['service__title'],
                    'username': ex_srv['customer__username']
                }
            )
            print(log)
        expired_services.delete()

    # Automatically connect new service
    for ex in CustomerService.objects.filter(
        deadline__lt=now,
        customer__auto_renewal_service=True
    ).exclude(customer=None).iterator():
        customer = ex.customer
        srv = ex.service
        cost = round(srv.cost, 2)
        if customer.balance >= cost:
            # can continue service
            with transaction.atomic():
                customer.balance -= cost
                ex.start_time = now
                ex.deadline = None  # Deadline sets automatically in signal pre_save
                ex.save(update_fields=('start_time', 'deadline'))
                customer.save(update_fields=('balance',))
                # make log about it
                log = CustomerLog.objects.create(
                    customer=customer, cost=-cost,
                    comment="Автоматическое продление услуги '%s' для %s" % (srv.title, customer)
                )
                print(log.comment)
        else:
            # finish service
            with transaction.atomic():
                ex.delete()
                log = CustomerLog.objects.create(
                    customer_id=ex.customer_id,
                    cost=0,
                    author=None,
                    date=now,
                    comment="Срок действия услуги '%(service_name)s' истёк" % {
                        'service_name': ex.service.title
                    }
                )
                print(log.comment)

    # Post connect service
    # connect service when autoconnect is True, and user have enough money
    for c in Customer.objects.filter(
        is_active=True,
        current_service=None,
        auto_renewal_service=True
    ).exclude(last_connected_service=None).iterator():
        try:
            srv = c.last_connected_service
            if srv is None or srv.is_admin:
                continue
            c.pick_service(
                service=srv, author=None,
                comment="Автоматическое продление услуги '%s'" % srv.title
            )
        except LogicError as err:
            print(err)

    # manage periodic pays
    ppays = PeriodicPayForId.objects.filter(next_pay__lt=now) \
        .prefetch_related('account', 'periodic_pay')
    for pay in ppays:
        pay.payment_for_service(now=now)

    # sync subscribers on GW
    threads = tuple(NasSyncThread(gw) for gw in Gateway.objects.
                    annotate(usercount=Count('customer')).
                    filter(usercount__gt=0, enabled=True))
    for t in threads:
        t.start()
    for t in threads:
        t.join()


if __name__ == "__main__":
    try:
        main()
    except (GatewayNetworkError, GatewayFailedResult) as e:
        print("Error while sync gateway:", e)
    except LogicError as e:
        print("Notice while sync gateway:", e)
