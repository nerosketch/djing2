from datetime import datetime, timedelta
from decimal import Decimal
from ipaddress import IPv4Address, AddressValueError
from typing import Optional, Type

from django.contrib.sites.models import Site
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models, transaction, IntegrityError
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.settings import api_settings

from customers.models import Customer, CustomerLog
from djing2.lib import LogicError, safe_int
from djing2.models import BaseAbstractModel
from groupapp.models import Group
from profiles.models import BaseAccount
from services.custom_logic import (
    SERVICE_CHOICES,
)
from services.custom_logic.base_intr import ServiceBase
from services import custom_signals
from services import schemas
from ._general import NotEnoughMoney


class ServiceManager(models.Manager):
    def get_services_by_group(self, group_id):
        return self.filter(groups__id__in=group_id)


class Service(BaseAbstractModel):
    title = models.CharField(_("Service title"), max_length=128)
    descr = models.TextField(_("Service description"), null=True, blank=True, default=None)
    speed_in = models.FloatField(
        _("Speed in"),
        validators=[
            MinValueValidator(limit_value=0.1),
        ],
    )
    speed_out = models.FloatField(
        _("Speed out"),
        validators=[
            MinValueValidator(limit_value=0.1),
        ],
    )
    speed_burst = models.FloatField(
        _("Speed burst"),
        help_text=_("Result burst = speed * speed_burst, speed_burst must be >= 1.0"),
        default=1.0,
        validators=[
            MinValueValidator(limit_value=1.0),
        ],
    )
    cost = models.DecimalField(
        verbose_name=_("Cost"),
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(limit_value=0.0)]
    )
    calc_type = models.PositiveSmallIntegerField(_("Script"), choices=SERVICE_CHOICES)
    is_admin = models.BooleanField(_("Tech service"), default=False)
    groups = models.ManyToManyField(Group, blank=True, verbose_name=_("Groups"))
    sites = models.ManyToManyField(Site, blank=True)
    create_time = models.DateTimeField(_("Create time"), auto_now_add=True, null=True, blank=True)

    objects = ServiceManager()

    @property
    def calc_type_name(self):
        logic_class = self.get_calc_type()
        if hasattr(logic_class, "description"):
            return getattr(logic_class, "description")
        return str(logic_class)

    def get_calc_type(self) -> Type[ServiceBase]:
        """
        :return: Child of services.base_intr.ServiceBase,
                 methods which provide the desired logic of payments
        """
        calc_code = self.calc_type
        for choice_pair in SERVICE_CHOICES:
            choice_code, logic_class = choice_pair
            if choice_code == calc_code:
                if not issubclass(logic_class, ServiceBase):
                    raise TypeError
                return logic_class
        raise RuntimeError('Unknown service.calc_type')

    def calc_deadline(self):
        calc_type = self.get_calc_type()
        deadline = calc_type.offer_deadline(
            start_time=datetime.now()
        )
        return deadline

    def calc_deadline_formatted(self):
        dtime_fmt = getattr(api_settings, "DATETIME_FORMAT", "%Y-%m-%d %H:%M")
        return self.calc_deadline().strftime(dtime_fmt)

    @property
    def planned_deadline(self):
        return self.calc_deadline_formatted()

    def pick_service(self, customer: Customer,
                     author: Optional[BaseAccount],
                     comment: Optional[str] = None,
                     deadline: Optional[datetime] = None,
                     allow_negative=False):

        if not isinstance(customer, Customer):
            raise TypeError('customer must be instance of customers.Customer')

        if self.is_admin and author is not None:
            if not author.is_staff:
                raise LogicError(_("User who is no staff can not buy admin services"))

        if allow_negative and (author is None or not author.is_staff):
            raise LogicError(_("User, who is no staff, can not be buy services on credit"))

        cost = self.cost

        # if not enough money
        if not allow_negative and customer.balance < cost:
            raise NotEnoughMoney(
                _("%(uname)s not enough money for service %(srv_name)s")
                % {"uname": customer.username, "srv_name": self}
            )

        custom_signals.customer_service_pre_pick.send(
            sender=Customer,
            instance=customer,
            service=self
        )

        try:
            with transaction.atomic():
                CustomerService.objects.create(
                    customer=customer,
                    service=self,
                    start_time=datetime.now(),
                    deadline=deadline,
                    cost=self.cost
                )

                customer.add_balance(
                    profile=author,
                    cost=-cost,
                    comment=comment or _("Buy service default log")
                )
        except IntegrityError:
            # if constraint unique_together['customer', 'service'] is raised
            raise LogicError(_("That service already activated"))

        custom_signals.customer_service_post_pick.send(
            sender=Customer,
            instance=customer,
            service=self
        )

    def __str__(self):
        return f"{self.title} ({self.cost:.2f})"

    class Meta:
        db_table = "services"
        verbose_name = _("Service")
        verbose_name_plural = _("Services")
        unique_together = ("speed_in", "speed_out", "cost", "calc_type")


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
            schemas.CustomerServiceTypeReportCalcType(
                calc_type_count=active_customers_with_services_qs.filter(
                    current_service__service__calc_type=srv_choice_num
                ).count(),
                service_descr=str(srv_choice_class.description),
            )
            for srv_choice_num, srv_choice_class in SERVICE_CHOICES
        ]

        return schemas.CustomerServiceTypeReportResponseSchema(
            all_count=all_count,
            admin_count=admin_count,
            zero_cost_count=zero_cost,
            calc_type_counts=calc_type_counts,
        )

    def activity_report(self) -> schemas.ActivityReportResponseSchema:
        qs = self.get_queryset()
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


RADIUS_SESSION_TIME = getattr(settings, "RADIUS_SESSION_TIME", 3600)


class CustomerService(BaseAbstractModel):
    customer = models.OneToOneField(
        Customer,
        # TODO: change current_service usages. And change to ForeignKey
        related_name='current_service',
        on_delete=models.CASCADE,
    )
    service = models.ForeignKey(
        Service,
        related_name="link_to_service",
        on_delete=models.CASCADE,
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
    cost = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(limit_value=0.0)]
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
        return CustomerService.objects.filter(
            customer__customeripleasemodel__ip_address=str(ip_addr),
            customer__is_active=True
        ).select_related('service', 'customer').first()

    def assign_deadline(self):
        calc_obj = self.service.get_calc_type()(self)
        self.deadline = calc_obj.calc_deadline()

    def continue_for_customer(self, now: Optional[datetime] = None):
        customer = self.customer
        service = self.service
        cost = service.cost
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
                to_balance=old_balance - float(cost),
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

    def stop_service(self, author_profile: Optional[BaseAccount],
                     comment: Optional[str] = None,
                     force_cost: Optional[Decimal] = None
                     ) -> None:

        custom_signals.customer_service_pre_stop.send(
            sender=CustomerService,
            instance=self,
            customer=self.customer
        )

        cost_to_return = force_cost
        if cost_to_return is None:
            cost_to_return = self.calc_cost_to_return()

        with transaction.atomic():
            if cost_to_return >= 0.1:
                self.customer.add_balance(
                    profile=author_profile,
                    cost=cost_to_return,
                    comment=comment or _("End of service, refund of balance")
                )
            else:
                self.customer.add_balance(
                    profile=author_profile,
                    cost=Decimal(0),
                    comment=comment or _("End of service")
                )
            custom_signals.customer_service_post_stop.send(
                sender=CustomerService,
                instance=self,
                customer=self.customer
            )
            self.delete()

    def calc_cost_to_return(self):
        """
        calculates total proportional cost from elapsed time,
        and return reminder to the account if reminder more than 0
        :return: None
        """
        service = self.service
        if not service:
            return
        calc = service.get_calc_type()(customer_service=self)
        elapsed_cost = calc.calc_cost(
            req_time=datetime.now()
        )
        total_cost = service.cost
        return total_cost - elapsed_cost

    def __str__(self):
        return self.service.title

    objects = CustomerServiceModelManager()

    class Meta:
        db_table = "customer_service"
        verbose_name = _("Customer service")
        verbose_name_plural = _("Customer services")
        unique_together = ('customer', 'service')
        permissions = [
            ("can_view_service_type_report", _('Can view service type report')),
            ("can_view_activity_report", _("Can view activity_report")),
        ]
