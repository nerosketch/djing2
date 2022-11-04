from typing import Optional
from ipaddress import AddressValueError, IPv4Address
from datetime import datetime, timedelta, date

from customers.models import CustomerLog, Customer
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _
from django.db import connection, models, transaction
from django.conf import settings
from djing2.models import BaseAbstractModel
from djing2.lib import LogicError, safe_float, safe_int, ProcessLocked, get_past_time_days
from profiles.models import UserProfile
from services.custom_logic import SERVICE_CHOICES
from services.models import OneShotPay, PeriodicPay, Service
from . import custom_signals
from . import schemas


RADIUS_SESSION_TIME = getattr(settings, "RADIUS_SESSION_TIME", 3600)


class CustomerServiceQuerySet(models.QuerySet):
    def _filter_raw_manage_customer_service(self, balance_equal_operator: str, customer_id=None):
        """
        Фильтруем истёкшие абонентские услуги, которые закончились
        или которые можно автоматически продлить.
        :param balance_equal_operator: Как сравниваем баланс абонента
                и стоимость услуги.
        :param customer_id: Если передано то фильтруем ещё и по абоненту.
        :return: RawQuerySet
        """
        # TODO: test it
        query = [
            "select cs.* from customer_service cs",
            "left join customers c on cs.id = c.current_service_id",
            "left join services s on cs.service_id = s.id",
            "where",
            "cs.deadline < now() and",
            "c.auto_renewal_service and",
            "c.balance %s s.cost" % balance_equal_operator,
            ]
        customer_id = safe_int(customer_id)
        params = None
        if customer_id > 0:
            query.append("and c.baseaccount_ptr_id = %s")
            params = [customer_id]
        query = " ".join(query)
        return self.raw(raw_query=query, params=params)

    def filter_auto_continue_raw(self, customer_id=None):
        return self._filter_raw_manage_customer_service(
            customer_id=customer_id,
            balance_equal_operator=">="
        )

    def filter_expired_raw(self, customer_id=None):
        return self._filter_raw_manage_customer_service(
            customer_id=customer_id,
            balance_equal_operator="<"
        )


class CustomerServiceModelManager(models.Manager):
    _queryset_class = CustomerServiceQuerySet

    def customer_service_type_report(self) -> schemas.CustomerServiceTypeReportResponseSchema:
        active_customers_with_services_qs = super().get_queryset().filter(
            is_active=True
        ).exclude(
            current_service=None
        )
        all_count = active_customers_with_services_qs.count()
        admin_count = active_customers_with_services_qs.filter(
            current_service__service__is_admin=True
        ).count()
        zero_cost = active_customers_with_services_qs.filter(
            current_service__service__cost=0
        ).count()

        calc_type_counts = [
            {
                "calc_type_count": active_customers_with_services_qs.filter(
                    current_service__service__calc_type=srv_choice_num
                ).count(),
                "service_descr": str(srv_choice_class.description),
            }
            for srv_choice_num, srv_choice_class in SERVICE_CHOICES
        ]

        return schemas.CustomerServiceTypeReportResponseSchema(
            all_count=all_count,
            admin_count=admin_count,
            zero_cost_count=zero_cost,
            calc_type_counts=calc_type_counts,
        )

    @staticmethod
    def finish_services_if_expired(profile: Optional[UserProfile] = None,
                                   comment=None, customer=None) -> None:
        # TODO: test it
        """
        If customer service has expired, and automatic connect
         is disabled, then finish that service and log about it
        :param profile: Instance of profiles.models.UserProfile.
        :param comment: comment for log
        :param customer: This is Customer instance, if doing it for him alone
        :return: nothing
        """
        if comment is None:
            comment = _("Service for customer %(customer_name)s with name '%(service_name)s' has expired")
        now = datetime.now()
        expired_services = CustomerService.objects.filter(
            deadline__lt=now,
            customer__auto_renewal_service=False
        )
        if customer is not None and isinstance(customer, Customer):
            expired_services = expired_services.filter(customer=customer)
        if expired_services.exists():
            expired_services = expired_services.select_related("customer", "service")
            with transaction.atomic():
                for exp_srv in expired_services.iterator():
                    if not hasattr(exp_srv, "customer"):
                        continue
                    exp_srv_customer = exp_srv.customer
                    CustomerLog.objects.create(
                        customer=exp_srv_customer,
                        cost=0,
                        author=profile if isinstance(profile, UserProfile) else None,
                        comment=comment % {
                            "customer_name": exp_srv_customer.get_short_name(),
                            "service_name": exp_srv.service.title
                        },
                    )
                    custom_signals.customer_service_post_stop.send(
                        sender=CustomerService,
                        instance=exp_srv,
                        customer=exp_srv_customer
                    )
                expired_services.delete()

    def activity_report(self) -> schemas.ActivityReportResponseSchema:
        qs = super().get_queryset()
        all_count = qs.count()
        enabled_count = qs.filter(is_active=True).count()
        with_services_count = qs.filter(
            is_active=True
        ).exclude(
            current_service=None
        ).count()

        active_count = (
            qs.annotate(ips=models.Count("customeripleasemodel"))
                .filter(is_active=True, ips__gt=0)
                .exclude(current_service=None)
                .count()
        )

        commercial_customers = qs.filter(
            is_active=True,
            current_service__service__is_admin=False,
            current_service__service__cost__gt=0
        ).exclude(current_service=None).count()

        return schemas.ActivityReportResponseSchema(
            all_count=all_count,
            enabled_count=enabled_count,
            with_services_count=with_services_count,
            active_count=active_count,
            commercial_customers=commercial_customers,
        )

    @staticmethod
    def continue_services_if_autoconnect(customer=None) -> None:
        # TODO: test it
        """
        If customer service has expired and automatic connect
        is enabled, then update service start_time, deadline,
        and flush money from customer balance
        :param customer: This is Customer instance, if doing it for him alone
        :return: nothing
        """
        now = datetime.now()
        expired_services = CustomerService.objects.select_related(
            'customer', 'service'
        ).filter(
            deadline__lte=now,
            customer__auto_renewal_service=True
        )
        if isinstance(customer, Customer):
            expired_services = expired_services.filter(customer=customer)
        for expired_service in expired_services.iterator():
            if not hasattr(expired_service, "customer"):
                continue
            expired_service_customer = expired_service.customer
            service = expired_service.service
            if expired_service_customer.balance >= service.cost:
                # can continue service
                expired_service.continue_for_customer(now=now)
            else:
                # finish service otherwise
                expired_service_customer.stop_service(
                    author_profile=None,
                    comment=_("Service '%(service_name)s' has expired") % {
                        "service_name": service.title
                    },
                    force_cost=0.0
                )


class CustomerService(BaseAbstractModel):
    current_service = models.OneToOneField(
        Customer,
        related_name='current_service',
        on_delete=models.CASCADE,
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="link_to_service"
    )
    start_time = models.DateTimeField(
        null=True,
        blank=True,
        default=None
    )
    deadline = models.DateTimeField(
        null=True,
        blank=True,
        default=None
    )

    def calc_service_cost(self) -> float:
        cost = self.service.cost
        return round(cost, 2)

    def calc_remaining_time(self) -> timedelta:
        now = datetime.now()
        dl = self.deadline
        elapsed = dl - now
        return elapsed

    def calc_session_time(self) -> timedelta:
        """
        If remaining time more than session time then return session time,
        return remaining time otherwise.
        :return: RADIUS_SESSION_TIME when time diff is too long,
        else return current session time
        """
        remaining_time = self.calc_remaining_time()
        radius_session_time = timedelta(
            seconds=RADIUS_SESSION_TIME
        )
        if remaining_time > radius_session_time:
            return radius_session_time
        return remaining_time

    @staticmethod
    def get_user_credentials_by_ip(ip_addr: str) -> Optional['CustomerService']:
        if not ip_addr:
            return None
        try:
            ip_addr = IPv4Address(ip_addr)
        except AddressValueError:
            return None
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM find_customer_service_by_ip(%s::inet)", (str(ip_addr),))
            res = cur.fetchone()
        if res is None:
            return None
        f_id, f_speed_in, f_speed_out, f_cost, f_calc_type, f_is_admin, f_speed_burst, f_start_time, f_deadline = res
        if f_id is None:
            return None
        srv = Service(
            pk=f_id,
            title=None,
            descr=None,
            speed_in=f_speed_in,
            speed_out=f_speed_out,
            speed_burst=f_speed_burst,
            cost=f_cost,
            calc_type=f_calc_type,
            is_admin=f_is_admin,
        )
        return CustomerService(
            service=srv,
            start_time=f_start_time,
            deadline=f_deadline
        )

    @staticmethod
    def find_customer_service_by_device_credentials(customer_id: int, current_service_id: int):
        # TODO: deprecated. Remove it. Function lost semantic, and not used.
        customer_id = safe_int(customer_id)
        current_service_id = safe_int(current_service_id)
        # TODO: make tests for it
        with connection.cursor() as cur:
            query = "SELECT * FROM find_customer_service_by_device_credentials(%s, %s)"
            cur.execute(query, [customer_id, current_service_id])
            res = cur.fetchone()
        if res is None or res[0] is None:
            return None
        (
            customer_service_id,
            service_id,
            speed_in,
            speed_out,
            cost,
            calc_type,
            is_admin,
            speed_burst,
            start_time,
            deadline,
        ) = res

        srv = Service(
            pk=service_id,
            title="",
            descr="",
            speed_in=float(speed_in),
            speed_out=float(speed_out),
            cost=float(cost),
            calc_type=calc_type,
            is_admin=is_admin,
            speed_burst=speed_burst,
        )
        customer_service = CustomerService(
            pk=customer_service_id,
            service=srv,
            start_time=start_time,
            deadline=deadline
        )
        return customer_service

    def assign_deadline(self):
        calc_obj = self.service.get_calc_type()(self)
        self.deadline = calc_obj.calc_deadline()

    def continue_for_customer(self, now: Optional[datetime] = None):
        customer = self.customer
        service = self.service
        cost = float(service.cost)
        old_balance = float(customer.balance)
        with transaction.atomic():
            customer.balance -= cost
            self.start_time = now or datetime.now()
            self.assign_deadline()
            self.save(update_fields=["start_time", "deadline"])
            customer.save(update_fields=["balance"])
            # make log about it
            uname = customer.get_short_name()
            CustomerLog.objects.create(
                customer=customer,
                cost=-cost,
                from_balance=old_balance,
                to_balance=old_balance - cost,
                comment=_("Automatic connect new service %(service_name)s "
                          "for %(customer_name)s") % {
                            "service_name": service.title,
                            "customer_name": uname
                        }
            )

    def clean(self) -> None:
        if self.deadline <= self.start_time:
            raise ValidationError(_("Deadline can't be in past"))

    def save(self, *args, **kwargs) -> None:
        self.full_clean(exclude=None)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.service.title

    objects = CustomerServiceModelManager()

    class Meta:
        db_table = "customer_service"
        verbose_name = _("Customer service")
        verbose_name_plural = _("Customer services")
        permissions = [
            ("can_view_service_type_report", _('Can view service type report')),
            ("can_view_activity_report", _("Can view activity_report")),
        ]

