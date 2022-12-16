import re
from datetime import datetime, timedelta, date
from typing import Optional, Generator
from decimal import Decimal

from addresses.interfaces import IAddressContaining
from addresses.models import AddressModel
from bitfield import BitField
from django.conf import settings
from django.core import validators
from django.db import connection, models, transaction
from django.utils.translation import gettext as _
from djing2.lib import ProcessLocked, get_past_time_days
from djing2.lib.mixins import RemoveFilterQuerySetMixin
from djing2.models import BaseAbstractModel
from dynamicfields.models import AbstractDynamicFieldContentModel
from encrypted_model_fields.fields import EncryptedCharField
from groupapp.models import Group
from profiles.models import BaseAccount, MyUserManager, UserProfile
from pydantic import BaseModel

from . import custom_signals


class CustomerLog(BaseAbstractModel):
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE)
    cost = models.FloatField(default=0.0)
    from_balance = models.FloatField(_('From balance'), default=0.0)
    to_balance = models.FloatField(_('To balance'), default=0.0)
    author = models.ForeignKey(
        BaseAccount,
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True
    )
    comment = models.CharField(max_length=128)
    date = models.DateTimeField(auto_now_add=True)

    @property
    def author_name(self) -> Optional[str]:
        if self.author:
            return str(self.author.get_full_name())

    class Meta:
        db_table = "customer_log"

    def __str__(self):
        return self.comment


class CustomerQuerySet(RemoveFilterQuerySetMixin, models.QuerySet):
    def filter_customers_by_address(self, addr_id: int):
        addr_ids_raw_query = AddressModel.objects.get_address_recursive_ids(addr_id=addr_id)
        # FIXME: "Cannot filter a query once a slice has been taken."
        return self.remove_filter('address_id').filter(
            address_id__in=addr_ids_raw_query
        )


class CustomerAFKType(BaseModel):
    timediff: timedelta
    last_date: date
    customer_id: int
    customer_uname: str
    customer_fio: str


class CustomerManager(MyUserManager):
    def get_queryset(self):
        return super().get_queryset().filter(is_admin=False)

    def create_user(self, telephone, username, password=None, *args, **kwargs):
        if not telephone:
            raise ValueError(_("Users must have an telephone number"))

        user = self.model(
            telephone=telephone,
            username=username,
            *args, **kwargs
        )
        user.is_admin = False

        user.set_password(password)
        user.save(using=self._db)
        return user

    @staticmethod
    def filter_long_time_inactive_customers(
        since_time: Optional[datetime] = None,
        out_limit=50
    ) -> Generator[CustomerAFKType, None, None]:
        """Who's not used services long time"""

        if not isinstance(since_time, datetime):
            # date_limit default is month
            since_time = get_past_time_days(
                how_long_days=60
            )

        with connection.cursor() as cur:
            cur.execute("select * from fetch_customers_by_not_activity(%s, %s);", [
                since_time, int(out_limit)
            ])
            res = cur.fetchone()
            while res is not None:
                timediff, last_date, customer_id, customer_uname, customer_fio = res
                yield CustomerAFKType(
                    timediff=timediff,
                    last_date=last_date,
                    customer_id=customer_id,
                    customer_uname=customer_uname,
                    customer_fio=customer_fio
                )
                res = cur.fetchone()


class Customer(IAddressContaining, BaseAccount):
    __before_is_active: bool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__before_is_active = bool(self.is_active)

    group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None,
        verbose_name=_("Customer group")
    )
    address = models.ForeignKey(
        AddressModel,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None
    )
    balance = models.DecimalField(
        default=0.0,
        max_digits=8,
        decimal_places=2
    )

    description = models.TextField(
        _("Comment"),
        null=True,
        blank=True,
        default=None
    )

    device = models.ForeignKey(
        "devices.Device",
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL
    )
    dev_port = models.ForeignKey(
        "devices.Port",
        null=True,
        blank=True,
        default=None,
        on_delete=models.SET_NULL
    )
    is_dynamic_ip = models.BooleanField(
        _("Is dynamic ip"),
        default=False
    )
    gateway = models.ForeignKey(
        "gateways.Gateway",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Gateway"),
        help_text=_("Network access server"),
        default=None,
    )
    auto_renewal_service = models.BooleanField(
        _("Automatically connect next service"),
        default=False
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
        ("icon_red_tel", _("Red phone")),
        ("icon_green_tel", _("Green phone")),
        ('icon_doc', _('Document')),
        ('icon_reddoc', _('Red document')),
    )
    markers = BitField(flags=MARKER_FLAGS, default=0)

    objects = CustomerManager.from_queryset(CustomerQuerySet)()

    passportinfo: 'PassportInfo'
    current_service: object  # services.CustomerService

    def save(self, *args, **kwargs):
        curr_is_active = bool(self.is_active)
        if self.__before_is_active and not curr_is_active:
            # Disabling customer
            custom_signals.customer_turns_off.send(
                sender=self.__class__,
                instance=self
            )
        elif not self.__before_is_active and curr_is_active:
            # Enabling customer
            custom_signals.customer_turns_on.send(
                sender=self.__class__,
                instance=self
            )
        return super().save(*args, **kwargs)

    def get_flag_icons(self) -> tuple:
        """
        Return icon list of set flags from self.markers
        :return: ['icon-donkey', 'icon-tv', ...]
        """
        if self.markers:
            return tuple(name for name, state in self.markers if state)
        return ()

    def set_markers(self, flag_names: list[str]):
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
        return getattr(self, 'current_service', None)

    def add_balance(self, profile: Optional[BaseAccount], cost: Decimal, comment: str) -> None:
        old_balance = float(self.balance)
        with transaction.atomic():
            CustomerLog.objects.create(
                customer=self,
                cost=float(cost),
                from_balance=old_balance,
                to_balance=old_balance + float(cost),
                author=profile if isinstance(profile, BaseAccount) else None,
                comment=re.sub(r"\s+", " ", str(comment))[:128].strip() if comment else '-'
            )
            self.balance += cost
            self.save(update_fields=['balance'])

    def get_address(self):
        return self.address

    # is customer have access to service,
    # view in services.custom_tariffs.<ServiceBase>.is_access()
    def is_access(self) -> bool:
        if not self.is_active:
            return False
        customer_service = self.active_service()
        if customer_service is None:
            return False
        trf = customer_service.service
        ct = trf.get_calc_type()(customer_service)
        return ct.is_access(self)

    @property
    def full_address(self):
        if self.address:
            return str(self.address.full_title())
        return '-'

    @staticmethod
    def set_service_group_accessory(group: Group, wanted_service_ids: list[int],
                                    current_user: UserProfile, current_site):
        if current_user.is_superuser:
            existed_service_ids = frozenset(t.id for t in group.service_set.all())
        else:
            existed_services = group.service_set.filter(sites__in=[current_site])
            existed_service_ids = frozenset(t.id for t in existed_services)
        wanted_service_ids = frozenset(map(int, wanted_service_ids))
        sub = existed_service_ids - wanted_service_ids
        add = wanted_service_ids - existed_service_ids
        group.service_set.remove(*sub)
        group.service_set.add(*add)

    def ping_all_leases(self) -> tuple[str, bool]:
        leases = self.customeripleasemodel_set.all()
        if not leases.exists():
            return _("Customer has not ips"), False
        try:
            for lease in leases:
                if lease.ping_icmp():
                    return _("Ping ok"), True
                else:
                    # arping_enabled = getattr(settings, "ARPING_ENABLED", False)
                    if lease.ping_icmp(arp=False):
                        return _("arp ping ok"), True
            return _("no ping"), False
        except ProcessLocked:
            return _("Process locked by another process"), False
        except ValueError as err:
            return str(err), False

    @property
    def group_title(self) -> Optional[str]:
        if self.group:
            return str(self.group.title)

    @property
    def address_title(self):
        return self.full_address

    @property
    def device_comment(self):
        if self.device:
            return str(self.device.comment)

    @property
    def current_service_title(self):
        cs = self.active_service()
        if cs and cs.service:
            return str(cs.service.title)

    @property
    def service_id(self) -> Optional[int]:
        cs = self.active_service()
        if cs:
            return int(cs.pk)

    @property
    def raw_password(self) -> Optional[str]:
        raw_passw = getattr(self, 'customerrawpassword', None)
        if raw_passw is not None:
            return str(raw_passw.passw_text)

    @property
    def marker_icons(self) -> list[str]:
        return [i for i in self.get_flag_icons()]

    @property
    def full_name(self):
        return self.get_full_name()

    class Meta:
        db_table = "customers"
        permissions = [
            ("can_buy_service", _("Buy service perm")),
            ("can_add_balance", _("fill account")),
            ("can_add_negative_balance", _("Fill account balance on negative cost")),
            ("can_ping", _("Can ping")),
            ("can_complete_service", _("Can complete service")),
        ]
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")


class CustomerDynamicFieldContentModel(AbstractDynamicFieldContentModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

    class Meta:
        db_table = 'dynamic_field_content'
        unique_together = ('customer', 'field')


class InvoiceForPayment(BaseAbstractModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    cost = models.FloatField(default=0.0)
    comment = models.CharField(max_length=128)
    date_create = models.DateTimeField(auto_now_add=True)
    date_pay = models.DateTimeField(blank=True, null=True)
    author = models.ForeignKey(
        UserProfile,
        related_name="+",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None
    )

    def __str__(self):
        return f"{self.customer.username} -> {self.cost:.2f}"

    def set_ok(self):
        self.status = True
        self.date_pay = datetime.now()

    @property
    def author_name(self):
        if self.author:
            fn = getattr(self, 'author.get_full_name', None)
            if fn is None:
                return
            return fn()

    @property
    def author_uname(self):
        if self.author:
            fn = getattr(self, 'author.username', None)
            if fn is None:
                return
            return fn()

    class Meta:
        db_table = "customer_inv_pay"
        verbose_name = _("Debt")
        verbose_name_plural = _("Debts")


class PassportInfo(IAddressContaining, BaseAbstractModel):
    series = models.CharField(
        _("Passport serial"),
        max_length=4,
        validators=(validators.integer_validator,)
    )
    number = models.CharField(
        _("Passport number"),
        max_length=6,
        validators=(validators.integer_validator,)
    )
    distributor = models.CharField(
        _("Distributor"),
        max_length=512
    )
    date_of_acceptance = models.DateField(
        _("Date of acceptance")
    )
    division_code = models.CharField(
        _("Division code"),
        max_length=64,
        null=True,
        blank=True,
        default=None
    )
    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        default=None
    )
    registration_address = models.ForeignKey(
        AddressModel,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        default=None
    )

    def get_address(self):
        return self.registration_address

    def full_address(self) -> str:
        ra = self.get_address()
        if ra:
            return str(ra.full_title())
        return '-'

    @property
    def registration_address_title(self) -> str:
        return self.full_address()

    class Meta:
        db_table = "passport_info"
        verbose_name = _("Passport Info")
        verbose_name_plural = _("Passport Info")

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
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="additional_telephones"
    )
    telephone = models.CharField(
        max_length=16,
        verbose_name=_("Telephone"),
        # unique=True,
        validators=(
            validators.RegexValidator(
                getattr(settings, "TELEPHONE_REGEXP", r"^(\+[7893]\d{10,11})?$")
            ),
        ),
    )
    owner_name = models.CharField(max_length=127)
    create_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.owner_name} - ({self.telephone})"

    class Meta:
        db_table = "additional_telephones"
        unique_together = ('customer', 'telephone')
        verbose_name = _("Additional telephone")
        verbose_name_plural = _("Additional telephones")


class CustomerAttachment(BaseAbstractModel):
    title = models.CharField(max_length=64)
    doc_file = models.FileField(
        upload_to="customer_attachments/%Y/%m/",
        max_length=128
    )
    create_time = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    @property
    def author_name(self):
        if self.author:
            return str(self.author.get_full_name())

    @property
    def customer_name(self):
        if self.customer:
            return str(self.customer.get_full_name())

    class Meta:
        db_table = "customer_attachments"
