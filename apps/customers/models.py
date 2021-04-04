import re
from datetime import datetime, timedelta
from ipaddress import AddressValueError, IPv4Address
from typing import Optional, List

from bitfield import BitField
from django.conf import settings
from django.core import validators
from django.db import connection, models, transaction
from django.utils.translation import gettext as _
from encrypted_model_fields.fields import EncryptedCharField

from djing2.lib import LogicError, safe_float, safe_int
from djing2.models import BaseAbstractModel
from groupapp.models import Group
from profiles.models import BaseAccount, MyUserManager, UserProfile
from services.custom_logic import SERVICE_CHOICES
from services.models import OneShotPay, PeriodicPay, Service

from . import custom_signals

RADIUS_SESSION_TIME = getattr(settings, "RADIUS_SESSION_TIME", 3600)


class NotEnoughMoney(LogicError):
    pass


class CustomerServiceModelManager(models.QuerySet):
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
        return self._filter_raw_manage_customer_service(customer_id=customer_id, balance_equal_operator=">=")

    def filter_expired_raw(self, customer_id=None):
        return self._filter_raw_manage_customer_service(customer_id=customer_id, balance_equal_operator="<")


class CustomerService(BaseAbstractModel):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name="link_to_service")
    start_time = models.DateTimeField(null=True, blank=True, default=None)
    deadline = models.DateTimeField(null=True, blank=True, default=None)

    def calc_service_cost(self) -> float:
        cost = self.service.cost
        return round(cost, 2)

    def calc_remaining_time(self) -> timedelta:
        now = datetime.now()
        dl = self.deadline
        elapsed = dl - now
        return elapsed

    def calc_session_time(self, splice=False) -> timedelta:
        """
        If remaining time more than session time then return session time,
        return remaining time otherwise
        :param splice: If splice then return RADIUS_SESSION_TIME when
                time diff is too long.
        :return: Current session time
        """
        remaining_time = self.calc_remaining_time()
        if splice:
            radius_session_time = timedelta(seconds=RADIUS_SESSION_TIME)
            if remaining_time > radius_session_time:
                return radius_session_time
        return remaining_time

    @staticmethod
    def get_user_credentials_by_ip(ip_addr: str):
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
        return CustomerService(service=srv, start_time=f_start_time, deadline=f_deadline)

    @staticmethod
    def find_customer_service_by_device_credentials(customer_id: int, current_service_id: int):
        customer_id = safe_int(customer_id)
        current_service_id = safe_int(current_service_id)
        # TODO: make tests for it
        with connection.cursor() as cur:
            query = "SELECT * FROM " "find_customer_service_by_device_credentials(%s, %s)"
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
            pk=customer_service_id, service=srv, start_time=start_time, deadline=deadline
        )
        return customer_service

    def __str__(self):
        return self.service.title

    objects = CustomerServiceModelManager.as_manager()

    class Meta:
        db_table = "customer_service"
        verbose_name = _("Customer service")
        verbose_name_plural = _("Customer services")
        ordering = ("start_time",)


class CustomerStreet(BaseAbstractModel):
    name = models.CharField(max_length=64)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "customer_street"
        verbose_name = _("Street")
        verbose_name_plural = _("Streets")
        ordering = ("name",)


class CustomerLog(BaseAbstractModel):
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE)
    cost = models.FloatField(default=0.0)
    author = models.ForeignKey(BaseAccount, on_delete=models.SET_NULL, related_name="+", blank=True, null=True)
    comment = models.CharField(max_length=128)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "customer_log"
        ordering = ("-date",)

    def __str__(self):
        return self.comment


class CustomerManager(MyUserManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_admin=False)

    def create_user(self, telephone, username, password=None, *args, **kwargs):
        """
        Creates and saves a User with the given telephone,
        username and password.
        """
        if not telephone:
            raise ValueError(_("Users must have an telephone number"))

        user = self.model(telephone=telephone, username=username, *args, **kwargs)
        user.is_admin = False

        user.set_password(password)
        user.save(using=self._db)
        return user

    def customer_service_type_report(self):
        qs = super().get_queryset().filter(is_active=True).exclude(current_service=None)
        all_count = qs.count()
        admin_count = qs.filter(current_service__service__is_admin=True).count()
        zero_cost = qs.filter(current_service__service__cost=0).count()

        calc_type_counts = [
            {
                "calc_type_count": qs.filter(current_service__service__calc_type=sc_num).count(),
                "service_descr": str(sc_class.description),
            }
            for sc_num, sc_class in SERVICE_CHOICES
        ]

        return {
            "all_count": all_count,
            "admin_count": admin_count,
            "zero_cost_count": zero_cost,
            "calc_type_counts": calc_type_counts,
        }

    def activity_report(self):
        qs = super().get_queryset()
        all_count = qs.count()
        enabled_count = qs.filter(is_active=True).count()
        with_services_count = qs.filter(is_active=True).exclude(current_service=None).count()

        active_count = (
            qs.annotate(ips=models.Count("customeripleasemodel"))
            .filter(is_active=True, ips__gt=0)
            .exclude(current_service=None)
            .count()
        )

        commercial_customers = (
            qs.filter(is_active=True, current_service__service__is_admin=False, current_service__service__cost__gt=0)
            .exclude(current_service=None)
            .count()
        )

        return {
            "all_count": all_count,
            "enabled_count": enabled_count,
            "with_services_count": with_services_count,
            "active_count": active_count,
            "commercial_customers": commercial_customers,
        }

    @staticmethod
    def finish_services_if_expired(profile: Optional[UserProfile] = None, comment=None, customer=None) -> None:
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
            comment = _("Service for customer %(customer_name)s " "with name '%(service_name)s' has expired")
        now = datetime.now()
        expired_service = CustomerService.objects.filter(deadline__lt=now, customer__auto_renewal_service=False)
        if customer is not None and isinstance(customer, Customer):
            expired_service = expired_service.filter(customer=customer)
        if expired_service.exists():
            expired_service = expired_service.select_related("customer", "service")
            # TODO: Replace it logging by trigger from db
            for exp_srv in expired_service.iterator():
                if not hasattr(exp_srv, "customer"):
                    continue
                exp_srv_customer = exp_srv.customer
                with transaction.atomic():
                    CustomerLog.objects.create(
                        customer=exp_srv_customer,
                        cost=0,
                        author=profile if isinstance(profile, UserProfile) else None,
                        comment=comment
                        % {"customer_name": exp_srv_customer.get_short_name(), "service_name": exp_srv.service.title},
                    )
            custom_signals.customer_service_batch_pre_stop.send(
                sender=CustomerService, expired_services=expired_service
            )
            expired_service.delete()
            custom_signals.customer_service_batch_post_stop.send(
                sender=CustomerService, expired_services=expired_service
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
        expired_services = CustomerService.objects.filter(deadline__lt=now, customer__auto_renewal_service=True)
        if customer is not None and isinstance(customer, Customer):
            expired_services = expired_services.filter(customer=customer)
        if not expired_services.exists():
            return
        for expired_service in expired_services.iterator():
            if not hasattr(expired_service, "customer"):
                continue
            expired_service_customer = expired_service.customer
            service = expired_service.service
            cost = round(service.cost, 3)
            if expired_service_customer.balance >= cost:
                # can continue service
                with transaction.atomic():
                    expired_service_customer.balance -= cost
                    expired_service.start_time = now
                    # Deadline sets automatically in signal pre_save
                    expired_service.deadline = None
                    expired_service.save(update_fields=["start_time", "deadline"])
                    expired_service_customer.save(update_fields=["balance"])
                    # make log about it
                    uname = expired_service_customer.get_short_name()
                    CustomerLog.objects.create(
                        customer=expired_service_customer,
                        cost=-cost,
                        comment=_("Automatic connect new service " "%(service_name)s for %(customer_name)s")
                        % {"service_name": service.title, "customer_name": uname},
                    )
            else:
                # finish service otherwise
                with transaction.atomic():
                    custom_signals.customer_service_pre_stop.send(
                        sender=CustomerService, expired_service=expired_service
                    )
                    expired_service.delete()
                    CustomerLog.objects.create(
                        customer=expired_service_customer,
                        cost=0,
                        comment=_("Service '%(service_name)s' has expired") % {"service_name": service.title},
                    )
                    custom_signals.customer_service_post_stop.send(
                        sender=CustomerService, expired_service=expired_service
                    )


class Customer(BaseAccount):
    current_service = models.OneToOneField(
        CustomerService, null=True, blank=True, on_delete=models.SET_NULL, default=None
    )
    group = models.ForeignKey(
        Group, on_delete=models.SET_NULL, blank=True, null=True, default=None, verbose_name=_("Customer group")
    )
    balance = models.FloatField(default=0.0)

    # ip_address deprecated, marked for remove
    ip_address = models.GenericIPAddressField(verbose_name=_("Ip address"), null=True, blank=True, default=None)
    description = models.TextField(_("Comment"), null=True, blank=True, default=None)
    street = models.ForeignKey(
        CustomerStreet, on_delete=models.SET_NULL, null=True, blank=True, default=None, verbose_name=_("Street")
    )
    house = models.CharField(_("House"), max_length=12, null=True, blank=True, default=None)
    device = models.ForeignKey("devices.Device", null=True, blank=True, default=None, on_delete=models.SET_NULL)
    dev_port = models.ForeignKey("devices.Port", null=True, blank=True, default=None, on_delete=models.SET_NULL)
    is_dynamic_ip = models.BooleanField(_("Is dynamic ip"), default=False)
    gateway = models.ForeignKey(
        "gateways.Gateway",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Gateway"),
        help_text=_("Network access server"),
        default=None,
    )
    auto_renewal_service = models.BooleanField(_("Automatically connect next service"), default=False)
    last_connected_service = models.ForeignKey(
        Service,
        verbose_name=_("Last connected service"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        default=None,
    )
    MARKER_FLAGS = (
        ("icon_donkey", _("Donkey")),
        ("icon_fire", _("Fire")),
        ("icon_ok", _("Ok")),
        ("icon_king", _("King")),
        ("icon_tv", _("TV")),
        ("icon_smile", _("Smile")),
        ("icon_dollar", _("Dollar")),
        ("icon_service", _("Service")),
        ("icon_mrk", _("Marker")),
    )
    markers = BitField(flags=MARKER_FLAGS, default=0)

    objects = CustomerManager()

    def get_flag_icons(self) -> tuple:
        """
        Return icon list of set flags from self.markers
        :return: ['icon-donkey', 'icon-tv', ...]
        """
        return tuple(name for name, state in self.markers if state)

    def set_markers(self, flag_names: List[str]):
        flags = None
        for flag_name in flag_names:
            flag = getattr(Customer.markers, flag_name)
            if flag:
                if flags:
                    flags |= flag
                else:
                    flags = flag
        self.markers = flags
        self.save(update_fields=["markers"])

    def active_service(self):
        return self.current_service

    def add_balance(self, profile: UserProfile, cost: float, comment: str) -> None:
        CustomerLog.objects.create(
            customer=self,
            cost=cost,
            author=profile if isinstance(profile, UserProfile) else None,
            comment=re.sub(r"\W{1,128}", " ", comment),
        )
        self.balance += cost

    def pick_service(
        self, service, author: Optional[UserProfile], comment=None, deadline=None, allow_negative=False
    ) -> None:
        """
        Trying to buy a service if enough money.
        :param allow_negative: Allows negative balance
        :param service: instance of services.models.Service.
        :param author: Instance of profiles.models.UserProfile.
        Who connected this service. May be None if author is a system.
        :param comment: Optional text for logging this pay.
        :param deadline: Instance of datetime.datetime. Date when service is
        expired.
        :return: Nothing
        """
        if not isinstance(service, Service):
            raise TypeError("service must be instance of services.models.Service")

        cost = round(service.cost, 2)

        if service.is_admin and author is not None:
            if not author.is_staff:
                raise LogicError(_("User who is no staff can not buy admin services"))

        if self.current_service is not None:
            if self.current_service.service == service:
                # if service already connected
                raise LogicError(_("That service already activated"))
            else:
                # if service is present then speak about it
                raise LogicError(_("Service already activated"))

        if allow_negative and not author.is_staff:
            raise LogicError(_("User, who is no staff, can not be buy services on credit"))

        # if not enough money
        if not allow_negative and self.balance < cost:
            raise NotEnoughMoney(
                _("%(uname)s not enough money for service %(srv_name)s")
                % {"uname": self.username, "srv_name": service}
            )

        custom_signals.customer_service_pre_pick.send(sender=Customer, customer=self, service=service)
        with transaction.atomic():
            self.current_service = CustomerService.objects.create(deadline=deadline, service=service)
            updated_fields = ["balance", "current_service"]
            if self.last_connected_service != service:
                self.last_connected_service = service
                updated_fields.append("last_connected_service")

            # charge for the service
            self.balance -= cost

            self.save(update_fields=updated_fields)

            # make log about it
            # TODO: move it to db trigger
            CustomerLog.objects.create(
                customer=self, cost=-cost, author=author, comment=comment or _("Buy service default log")
            )
        custom_signals.customer_service_post_pick.send(sender=Customer, customer=self, service=service)

    def stop_service(self, profile: UserProfile) -> None:
        """
        Removing current connected customer service
        :param profile: Instance of profiles.models.UserProfile.
        :return: nothing
        """
        customer_service = self.active_service()
        custom_signals.customer_service_pre_stop.send(sender=CustomerService, expired_service=customer_service)
        with transaction.atomic():
            cost_to_return = self.calc_cost_to_return()
            if cost_to_return > 0.1:
                self.add_balance(profile, cost=cost_to_return, comment=_("End of service, refund of balance"))
                self.save(update_fields=("balance",))
            else:
                self.add_balance(profile, cost=0, comment=_("End of service"))
            customer_service.delete()
        custom_signals.customer_service_post_stop.send(sender=CustomerService, expired_service=customer_service)

    def make_shot(self, request, shot: OneShotPay, allow_negative=False, comment=None) -> bool:
        """
        Makes one-time service for accounting services.
        :param request: Django http request.
        :param shot: instance of services.OneShotPay model.
        :param allow_negative: Allows negative balance.
        :param comment: Optional text for logging this pay.
        :return: result for frontend
        """
        if not isinstance(shot, OneShotPay):
            return False

        cost = round(shot.calc_cost(request, self), 3)

        # if not enough money
        if not allow_negative and self.balance < cost:
            raise NotEnoughMoney(
                _("%(uname)s not enough money for service %(srv_name)s")
                % {"uname": self.username, "srv_name": shot.name}
            )
        with transaction.atomic():
            # charge for the service
            self.balance -= cost
            self.save(update_fields=["balance"])

            # make log about it
            CustomerLog.objects.create(
                customer=self,
                cost=-cost,
                author=request.user,
                comment=comment or _('Buy one-shot service for "%(title)s"') % {"title": shot.name},
            )
        return True

    def make_periodic_pay(self, periodic_pay: PeriodicPay, next_pay: datetime):
        ppay = PeriodicPayForId.objects.create(periodic_pay=periodic_pay, next_pay=next_pay, account=self)
        return ppay

    def calc_cost_to_return(self):
        """
        calculates total proportional cost from elapsed time,
        and return reminder to the account if reminder more than 0
        :return: None
        """
        customer_service = self.active_service()
        if not customer_service:
            return
        service = customer_service.service
        if not service:
            return
        calc = service.get_calc_type()(customer_service=customer_service)
        elapsed_cost = calc.calc_cost()
        total_cost = safe_float(service.cost)
        return total_cost - elapsed_cost

    # is customer have access to service,
    # view in services.custom_tariffs.<ServiceBase>.manage_access()
    def is_access(self) -> bool:
        if not self.is_active:
            return False
        customer_service = self.active_service()
        if customer_service is None:
            return False
        trf = customer_service.service
        ct = trf.get_calc_type()(customer_service)
        return ct.manage_access(self)

    def connect_service_if_autoconnect(self):
        """
        If customer service has expired, and then finished, and
        automatic continue is enabled, then connect new service
        from now
        :return: nothing
        """
        if not self.is_active:
            return
        if self.current_service:
            return
        if not self.auto_renewal_service:
            return
        if not self.last_connected_service:
            return

        srv = self.last_connected_service
        if not srv or srv.is_admin:
            return
        self.pick_service(
            service=srv,
            author=None,
            comment=_("Automatic connect service '%(service_name)s'") % {"service_name": srv.title},
        )

    def get_address(self):
        return f"{self.group}. {self.street} {self.house}"

    @staticmethod
    def set_service_group_accessory(group, wanted_service_ids: list, request):
        if request.user.is_superuser:
            existed_service_ids = frozenset(t.id for t in group.service_set.all())
        else:
            existed_services = group.service_set.filter(sites__in=[request.site])
            existed_service_ids = frozenset(t.id for t in existed_services)
        wanted_service_ids = frozenset(map(int, wanted_service_ids))
        sub = existed_service_ids - wanted_service_ids
        add = wanted_service_ids - existed_service_ids
        group.service_set.remove(*sub)
        group.service_set.add(*add)
        # Customer.objects.filter(
        #     group=group,
        #     last_connected_service__in=sub
        # ).update(last_connected_service=None)

    class Meta:
        db_table = "customers"
        permissions = [
            ("can_buy_service", _("Buy service perm")),
            ("can_add_balance", _("fill account")),
            ("can_ping", _("Can ping")),
            ("can_complete_service", _("Can complete service")),
        ]
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")
        ordering = ("fio",)
        unique_together = ("ip_address", "gateway")


class InvoiceForPayment(BaseAbstractModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    cost = models.FloatField(default=0.0)
    comment = models.CharField(max_length=128)
    date_create = models.DateTimeField(auto_now_add=True)
    date_pay = models.DateTimeField(blank=True, null=True)
    author = models.ForeignKey(
        UserProfile, related_name="+", on_delete=models.SET_NULL, blank=True, null=True, default=None
    )

    def __str__(self):
        return f"{self.customer.username} -> {self.cost:.2f}"

    def set_ok(self):
        self.status = True
        self.date_pay = datetime.now()

    class Meta:
        ordering = ("id",)
        db_table = "customer_inv_pay"
        verbose_name = _("Debt")
        verbose_name_plural = _("Debts")


class PassportInfo(BaseAbstractModel):
    series = models.CharField(_("Passport serial"), max_length=4, validators=(validators.integer_validator,))
    number = models.CharField(_("Passport number"), max_length=6, validators=(validators.integer_validator,))
    distributor = models.CharField(_("Distributor"), max_length=64)
    date_of_acceptance = models.DateField(_("Date of acceptance"))
    division_code = models.CharField(_("Division code"), max_length=64, null=True, blank=True, default=None)
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, blank=True, null=True, default=None)

    class Meta:
        db_table = "passport_info"
        verbose_name = _("Passport Info")
        verbose_name_plural = _("Passport Info")
        ordering = ("id",)

    def __str__(self):
        return f"{self.series} {self.number}"


class CustomerRawPassword(BaseAbstractModel):
    customer = models.OneToOneField(Customer, models.CASCADE)
    passw_text = EncryptedCharField(max_length=64)

    def __str__(self):
        return f"{self.customer} - {self.passw_text}"

    class Meta:
        db_table = "customer_raw_password"


class AdditionalTelephone(BaseAbstractModel):
    """Model for storing additional telephones

    Args:
        DjingModelViewSet ([type]): [description]
    """

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="additional_telephones")
    telephone = models.CharField(
        max_length=16,
        verbose_name=_("Telephone"),
        # unique=True,
        validators=(validators.RegexValidator(getattr(settings, "TELEPHONE_REGEXP", r"^(\+[7893]\d{10,11})?$")),),
    )
    owner_name = models.CharField(max_length=127)
    create_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.owner_name} - ({self.telephone})"

    class Meta:
        db_table = "additional_telephones"
        ordering = ("id",)
        verbose_name = _("Additional telephone")
        verbose_name_plural = _("Additional telephones")


class PeriodicPayForId(BaseAbstractModel):
    periodic_pay = models.ForeignKey(PeriodicPay, on_delete=models.CASCADE, verbose_name=_("Periodic pay"))
    last_pay = models.DateTimeField(_("Last pay time"), blank=True, null=True, default=None)
    next_pay = models.DateTimeField(_("Next time to pay"))
    account = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name=_("Account"))

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
                    author, -amount, comment=_('Charge for "%(service)s"') % {"service": self.periodic_pay}
                )
                account.save(update_fields=("balance",))
                self.last_pay = now
                self.next_pay = next_pay_date
                self.save(update_fields=("last_pay", "next_pay"))

    def __str__(self):
        return f"{self.periodic_pay} {self.next_pay}"

    class Meta:
        db_table = "periodic_pay_for_id"
        ordering = ("last_pay",)


class CustomerAttachment(BaseAbstractModel):
    title = models.CharField(max_length=64)
    doc_file = models.FileField(upload_to="customer_attachments/%Y/%m/", max_length=128)
    create_time = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "customer_attachments"
        ordering = ("id",)
