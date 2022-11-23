from datetime import datetime
from decimal import Decimal
from typing import Optional

from customers.models import Customer
from django.db import transaction, models
from django.utils.translation import gettext_lazy as _
from djing2.lib.logger import logger
from profiles.models import BaseAccount
from services import custom_signals
from services import models


def connect_service_from_queue(customer_id: int):
    with transaction.atomic():
        first_queue = models.CustomerServiceConnectingQueueModel.objects.filter(
            customer_id=customer_id
        ).pop_front()
        if first_queue is None:
            return
        try:
            srv = first_queue.service
            srv.pick_service(
                customer=first_queue.customer,
                author=None,
                comment=_("Automatic connect service '%(service_name)s'") % {
                    "service_name": srv.title
                }
            )
        except models.NotEnoughMoney as e:
            logger.info(str(e))


def continue_services_if_autoconnect(customer=None) -> None:
    """
    If customer service has expired and automatic connect
    is enabled, then update service start_time, deadline,
    and flush money from customer balance
    :param customer: This is Customer instance, if doing it for him alone
    :return: nothing
    """
    now = datetime.now()
    expired_services = models.CustomerService.objects.select_related(
        'customer', 'service'
    ).filter(
        deadline__lte=now,
        customer__auto_renewal_service=True
    ).exclude(customer=None)
    if isinstance(customer, Customer):
        expired_services = expired_services.filter(customer=customer)
    for expired_service in expired_services.iterator():
        expired_service_customer = expired_service.customer
        service = expired_service.service
        if expired_service_customer.balance >= service.cost:
            # can continue service
            expired_service.continue_for_customer(now=now)
        else:
            # finish service otherwise
            expired_service.stop_service(
                author_profile=None,
                comment=_("Service '%(service_name)s' has expired") % {
                    "service_name": service.title
                }
            )


def finish_services_if_expired(profile: Optional[BaseAccount] = None,
                               comment=None, customer=None) -> None:
    # TODO: test it
    """
    If customer service has expired, and automatic connect
     is disabled, then finish that service and log about it
    :param profile: Instance of profiles.models.BaseAccount.
    :param comment: comment for log
    :param customer: This is Customer instance, if doing it for him alone
    :return: nothing
    """
    if comment is None:
        comment = _("Service for customer %(customer_name)s with name '%(service_name)s' has expired")
    now = datetime.now()
    expired_services = models.CustomerService.objects.filter(
        deadline__lt=now,
        customer__auto_renewal_service=False
    ).select_related("customer", "service").exclude(customer=None)

    if customer is not None and isinstance(customer, Customer):
        expired_services = expired_services.filter(customer=customer)

    dec0 = Decimal(0)
    profile = profile if isinstance(profile, BaseAccount) else None

    if expired_services.exists():
        with transaction.atomic():
            for exp_srv in expired_services.iterator():
                exp_srv_customer = exp_srv.customer
                exp_srv_customer.add_balance(
                    profile=profile,
                    cost=dec0,
                    comment=comment % {
                        "customer_name": exp_srv_customer.get_short_name(),
                        "service_name": exp_srv.service.title
                    }
                )
                custom_signals.customer_service_post_stop.send(
                    sender=models.CustomerService,
                    instance=exp_srv,
                    customer=exp_srv_customer
                )
            expired_services.delete()


def manage_periodic_pays_run():
    now = datetime.now()
    ppays = models.PeriodicPayForId.objects.select_related("account", "periodic_pay").filter(
        next_pay__lte=now,
        # account__is_active=True
    )
    for pay in ppays.iterator():
        pay.payment_for_service(now=now)


def connect_service_if_autoconnect(customer_id: Optional[int] = None):
    """
    Connect service when autoconnect is True, and user have enough money
    """

    customers = Customer.objects.filter(
        is_active=True,
        auto_renewal_service=True,
        balance__gt=0
    ).annotate(
        connected_services_count=models.Count('current_service')
    ).filter(connected_services_count=0)

    if isinstance(customer_id, int):
        customers = customers.filter(pk=customer_id)

    queue_services = models.CustomerServiceConnectingQueueModel.objects.filter(
        customer__in=customers,
        service__is_admin=False
    ).select_related('service', 'customer').filter_first()

    for queue_item in queue_services.iterator():
        srv = queue_item.service
        try:
            srv.pick_service(
                customer=queue_item.customer,
                author=None,
                comment=_("Automatic connect service '%(service_name)s'") % {
                    "service_name": srv.title
                }
            )
        except models.NotEnoughMoney as e:
            logger.info(str(e))
