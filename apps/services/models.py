from datetime import datetime, timedelta
from decimal import Decimal
from ipaddress import IPv4Address, AddressValueError
from typing import Optional, Type

from django.contrib.sites.models import Site
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models, transaction, connection, IntegrityError
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework.settings import api_settings

from customers.models import Customer, CustomerLog
from djing2.lib import LogicError, safe_int
from djing2.models import BaseAbstractModel
from groupapp.models import Group
from profiles.models import BaseAccount, UserProfile
from services.custom_logic import (
    SERVICE_CHOICES,
    PERIODIC_PAY_CALC_DEFAULT,
    PERIODIC_PAY_CHOICES,
    ONE_SHOT_TYPES,
    ONE_SHOT_DEFAULT,
)
from services.custom_logic.base_intr import ServiceBase, PeriodicPayCalcBase, OneShotBaseService
from services import custom_signals
from services import schemas


class NotEnoughMoney(LogicError):
    default_detail = _("not enough money")


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
                % {"uname": author.username, "srv_name": self}
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


class PeriodicPay(BaseAbstractModel):
    name = models.CharField(_("Periodic pay name"), max_length=64)
    when_add = models.DateTimeField(_("When pay created"), auto_now_add=True)
    calc_type = models.PositiveSmallIntegerField(
        verbose_name=_("Script type for calculations"),
        default=PERIODIC_PAY_CALC_DEFAULT,
        choices=PERIODIC_PAY_CHOICES
    )
    amount = models.FloatField(_("Total amount"))
    extra_info = models.JSONField(_("Extra info"), null=True, blank=True)
    sites = models.ManyToManyField(Site, blank=True)

    def _get_calc_object(self):
        """
        :return: subclass of services.custom_logic.PeriodicPayCalcBase with required
        logic depending on the selected in database.
        """
        calc_code = self.calc_type
        for choice_pair in PERIODIC_PAY_CHOICES:
            choice_code, logic_class = choice_pair
            if choice_code == calc_code:
                if not issubclass(logic_class, PeriodicPayCalcBase):
                    raise TypeError
                return logic_class()

    def calc_type_name(self) -> str:
        ct = self._get_calc_object()
        desc = ct.description
        return str(desc)

    def get_next_time_to_pay(self, last_time_payment):
        #
        # last_time_payment may be None if it is a first payment
        #
        calc_obj = self._get_calc_object()
        res = calc_obj.get_next_time_to_pay(self, last_time_payment)
        if not isinstance(res, datetime):
            raise TypeError
        return res

    def calc_amount(self) -> float:
        calc_obj = self._get_calc_object()
        res = calc_obj.calc_amount(self)
        if not isinstance(res, float):
            raise TypeError
        return res

    def __str__(self):
        return self.name

    def make_periodic_pay(self, next_pay: datetime, customer: Customer):
        ppay = PeriodicPayForId.objects.create(
            periodic_pay=self,
            next_pay=next_pay,
            account=customer
        )
        return ppay

    class Meta:
        db_table = "periodic_pay"
        verbose_name = _("Periodic pay")
        verbose_name_plural = _("Periodic pays")


class OneShotPay(BaseAbstractModel):
    name = models.CharField(_("Shot pay name"), max_length=64)
    cost = models.FloatField(_("Total cost"))
    pay_type = models.PositiveSmallIntegerField(
        _("One shot pay type"),
        help_text=_("Uses for callbacks before pay and after pay"),
        choices=ONE_SHOT_TYPES,
        default=ONE_SHOT_DEFAULT,
    )
    _pay_type_cache = None
    sites = models.ManyToManyField(Site, blank=True)

    def _get_calc_object(self):
        """
        :return: subclass of services.custom_logic.OneShotBaseService with required
        logic depending on the selected in database.
        """
        if self._pay_type_cache is not None:
            return self._pay_type_cache
        pay_type = self.pay_type
        for choice_pair in ONE_SHOT_TYPES:
            choice_code, logic_class = choice_pair
            if choice_code == pay_type:
                if not issubclass(logic_class, OneShotBaseService):
                    raise TypeError
                self._pay_type_cache = logic_class()
                return self._pay_type_cache

    def before_pay(self, customer):
        pay_logic = self._get_calc_object()
        pay_logic.before_pay(customer=customer)

    def calc_cost(self, customer) -> float:
        pay_logic = self._get_calc_object()
        return pay_logic.calc_cost(self, customer)

    def after_pay(self, customer):
        pay_logic = self._get_calc_object()
        pay_logic.before_pay(customer=customer)

    def pick4customer(self, user_profile: UserProfile, customer: Customer,
                      allow_negative=False, comment=None):

        cost = Decimal(self.calc_cost(self))

        # if not enough money
        if not allow_negative and customer.balance < cost:
            raise NotEnoughMoney(
                detail=_("%(uname)s not enough money for service %(srv_name)s")
                       % {"uname": customer.username, "srv_name": self.name}
            )

        customer.add_balance(
            profile=user_profile,
            cost=-cost,
            comment=comment or _('Buy one-shot service for "%(title)s"') % {
                "title": self.name
            }
        )

    def __str__(self):
        return self.name

    class Meta:
        db_table = "service_one_shot"


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

    @staticmethod
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
        expired_services = CustomerService.objects.filter(
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
                        sender=CustomerService,
                        instance=exp_srv,
                        customer=exp_srv_customer
                    )
                expired_services.delete()

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

    @staticmethod
    def continue_services_if_autoconnect(customer=None) -> None:
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
            sql = (
                "SELECT "
                   "services.id, "
                   "services.speed_in, "
                   "services.speed_out, "
                   "services.cost, "
                   "services.calc_type, "
                   "services.is_admin, "
                   "services.speed_burst, "
                   "cs.start_time, "
                   "cs.deadline, "
                   "cs.customer_id "
                 "FROM services "
                   "LEFT JOIN customer_service cs ON (cs.service_id = services.id) "
                   "LEFT JOIN networks_ip_leases nil ON (nil.customer_id = cs.customer_id) "
                   "LEFT JOIN base_accounts ba ON (ba.id = cs.customer_id) "
                 "WHERE nil.ip_address = %s::inet AND ba.is_active "
                 "LIMIT 1;"
            )
            cur.execute(sql, [str(ip_addr)])
            res = cur.fetchone()
        if res is None:
            return None
        (
            f_id, f_speed_in, f_speed_out, f_cost, f_calc_type,
            f_is_admin, f_speed_burst, f_start_time, f_deadline,
            customer_id
        ) = res
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
            deadline=f_deadline,
            customer_id=customer_id
        )

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


class PeriodicPayForId(BaseAbstractModel):
    periodic_pay = models.ForeignKey(
        PeriodicPay,
        on_delete=models.CASCADE,
        verbose_name=_("Periodic pay")
    )
    last_pay = models.DateTimeField(
        _("Last pay time"),
        blank=True,
        null=True,
        default=None
    )
    next_pay = models.DateTimeField(_("Next time to pay"))
    account = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        verbose_name=_("Account")
    )

    def payment_for_service(self, author: UserProfile = None, now: Optional[datetime] = None):
        """
        Charge for the service and leave a log about it
        :param now: Current date, if now is None than it calculates in here
        :param author: instance of UserProfile
        """
        if now is None:
            now = datetime.now()
        if self.next_pay < now:
            pp = self.periodic_pay
            amount = pp.calc_amount()
            next_pay_date = pp.get_next_time_to_pay(self.last_pay)
            account = self.account
            with transaction.atomic():
                account.add_balance(
                    author, Decimal(-amount), comment=_('Charge for "%(service)s"') % {
                        "service": self.periodic_pay
                    }
                )
                account.save(update_fields=("balance",))
                self.last_pay = now
                self.next_pay = next_pay_date
                self.save(update_fields=("last_pay", "next_pay"))

    def __str__(self):
        return f"{self.periodic_pay} {self.next_pay}"

    @property
    def service_name(self):
        if self.periodic_pay:
            return str(self.periodic_pay.name)

    @property
    def service_calc_type(self):
        if self.periodic_pay:
            return self.periodic_pay.calc_type_name()

    @property
    def service_amount(self):
        if self.periodic_pay:
            return float(self.periodic_pay.amount)

    class Meta:
        db_table = "periodic_pay_for_id"


class CustomerServiceConnectingQueueModelManager(models.QuerySet):
    """
    Filter queue by number_queue, and returns only items with maximum in the group.
    """
    def filter_first_queue_items(self):
        return self.annotate(
            max_number_queue=models.Subquery(
                CustomerServiceConnectingQueueModel.objects.filter(
                    customer_id=models.OuterRef('customer'),
                    service_id=models.OuterRef('service')
                ).order_by('-number_queue').values('number_queue')[:1],
                output_field=models.IntegerField()
            )
        ).filter(
            number_queue=models.F('max_number_queue')
        )


class CustomerServiceConnectingQueueModel(models.Model):
    customer = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='service_queue',
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='customer_service_queue',
    )
    number_queue = models.IntegerField('Number in the queue')

    objects = CustomerServiceConnectingQueueModelManager.as_manager()

    class Meta:
        db_table = 'services_queue'
        unique_together = ('customer', 'number_queue')


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

    queue_services = CustomerServiceConnectingQueueModel.objects.filter(
        customer__in=customers,
        service__is_admin=False
    ).select_related('service', 'customer').filter_first_queue_items()

    for queue_item in queue_services.iterator():
        srv = queue_item.service
        srv.pick_service(
            customer=srv.customer,
            author=None,
            comment=_("Automatic connect service '%(service_name)s'") % {
                "service_name": srv.title
            }
        )
