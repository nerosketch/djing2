from datetime import datetime

from bitfield import BitField
from django.conf import settings
from django.core import validators
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.db.models.signals import post_init, pre_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _, gettext
from encrypted_model_fields.fields import EncryptedCharField

from djing2.lib import LogicError
from gateways.nas_managers import (
    SubnetQueue, GatewayFailedResult,
    GatewayNetworkError
)
from profiles.models import BaseAccount, MyUserManager, UserProfile
from services.models import Service, PeriodicPay
from groupapp.models import Group


class CustomerService(models.Model):
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='link_to_service'
    )
    start_time = models.DateTimeField(null=True, blank=True, default=None)
    deadline = models.DateTimeField(null=True, blank=True, default=None)

    def calc_amount_service(self):
        amount = self.service.cost
        return round(amount, 2)

    def __str__(self):
        return "%s: %s" % (
            self.deadline,
            self.service.title
        )

    class Meta:
        db_table = 'customer_service'
        permissions = (
            ('can_complete_service', _('finish service perm')),
        )
        verbose_name = _('Customer service')
        verbose_name_plural = _('Customer services')
        ordering = ('start_time',)


class CustomerStreet(models.Model):
    name = models.CharField(max_length=64)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'customer_street'
        verbose_name = _('Street')
        verbose_name_plural = _('Streets')
        ordering = 'name',


class CustomerLog(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE)
    cost = models.FloatField(default=0.0)
    author = models.ForeignKey(
        UserProfile, on_delete=models.SET_NULL,
        related_name='+', blank=True, null=True
    )
    comment = models.CharField(max_length=128)
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'customer_log'
        ordering = '-date',

    def __str__(self):
        return self.comment


class CustomerManager(MyUserManager):
    def get_queryset(self):
        return super(CustomerManager, self).get_queryset().filter(is_admin=False)


class Customer(BaseAccount):
    current_service = models.OneToOneField(
        CustomerService,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        default=None
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        blank=True, null=True,
        verbose_name=_('Customer group')
    )
    balance = models.FloatField(default=0.0)
    ip_address = models.GenericIPAddressField(
        verbose_name=_('Ip address'),
        null=True,
        blank=True
    )
    description = models.TextField(
        _('Comment'),
        null=True,
        blank=True
    )
    street = models.ForeignKey(
        CustomerStreet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Street')
    )
    house = models.CharField(
        _('House'),
        max_length=12,
        null=True,
        blank=True
    )
    device = models.ForeignKey(
        'devices.Device',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    dev_port = models.ForeignKey(
        'devices.Port',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    is_dynamic_ip = models.BooleanField(
        _('Is dynamic ip'),
        default=False
    )
    gateway = models.ForeignKey(
        'gateways.Gateway',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_('Gateway'),
        help_text=_('Network access server'),
        default=None
    )
    auto_renewal_service = models.BooleanField(
        _('Automatically connect next service'),
        default=False
    )
    last_connected_service = models.ForeignKey(
        Service, verbose_name=_('Last connected service'),
        on_delete=models.SET_NULL, null=True, blank=True, default=None
    )
    MARKER_FLAGS = (
        ('icon_donkey', _('Donkey')),
        ('icon_fire', _('Fire')),
        ('icon_ok', _('Ok')),
        ('icon_king', _('King')),
        ('icon_tv', _('TV')),
        ('icon_smile', _('Smile')),
        ('icon_dollar', _('Dollar')),
        ('icon_service', _('Service')),
        ('icon_mrk', _('Marker'))
    )
    markers = BitField(flags=MARKER_FLAGS, default=0)

    objects = CustomerManager()

    def get_flag_icons(self):
        """
        Return icon list of set flags from self.markers
        :return: ['m-icon-donkey', 'm-icon-tv', ...]
        """
        return tuple("m-%s" % name for name, state in self.markers if state)

    def active_service(self):
        return self.current_service

    def add_balance(self, profile, cost, comment):
        CustomerLog.objects.create(
            customer=self,
            cost=cost,
            author=profile if isinstance(profile, UserProfile) else None,
            comment=comment
        )
        self.balance += cost

    def pick_service(self, service, author, comment=None, deadline=None) -> None:
        """
        Trying to buy a service if enough money.
        :param service: instance of services.models.Service.
        :param author: Instance of profiles.models.UserProfile.
        Who connected this service. May be None if author is a system.
        :param comment: Optional text for logging this pay.
        :param deadline: Instance of datetime.datetime. Date when service is
        expired.
        :return: Nothing
        """
        if not isinstance(service, Service):
            raise TypeError

        amount = round(service.cost, 2)

        if service.is_admin and author is not None:
            if not author.is_staff:
                raise LogicError(
                    _('User that is no staff can not buy admin services')
                )

        if self.current_service is not None:
            if self.current_service.service == service:
                # if service already connected
                raise LogicError(_('That service already activated'))
            else:
                # if service is present then speak about it
                raise LogicError(_('Service already activated'))

        # if not enough money
        if self.balance < amount:
            raise LogicError(_('%s not enough money for service %s') % (
                self.username, service.title
            ))

        with transaction.atomic():
            self.current_service = CustomerService.objects.create(
                deadline=deadline, service=service
            )
            if self.last_connected_service != service:
                self.last_connected_service = service

            # charge for the service
            self.balance -= amount

            self.save(update_fields=(
                'balance',
                'current_service',
                'last_connected_service'
            ))

            # make log about it
            CustomerLog.objects.create(
                customer=self, cost=-amount,
                author=author,
                comment=comment or _('Buy service default log')
            )

    def attach_ip_addr(self, ip, strict=False):
        """
        Attach ip address to account
        :param ip: Instance of str or ip_address
        :param strict: If strict is True then ip not replaced quietly
        :return: None
        """
        if strict and self.ip_address:
            raise LogicError('Ip address already exists')
        self.ip_address = ip
        self.save(update_fields=('ip_address',))

    def free_ip_addr(self) -> bool:
        if self.ip_address:
            self.ip_address = None
            self.save(update_fields=('ip_address',))
            return True
        return False

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

    # make customer from agent structure
    def build_agent_struct(self):
        if not self.ip_address:
            return
        customer_service = self.active_service()
        if customer_service:
            service = customer_service.service
            return SubnetQueue(
                name="uid%d" % self.pk,
                network=self.ip_address,
                max_limit=(service.speed_in, service.speed_out),
                is_access=self.is_access()
            )

    def gw_sync_self(self):
        """
        Synchronize user with gateway
        :return:
        """
        if self.gateway is None:
            raise LogicError(_('gateway required'))
        try:
            agent_struct = self.build_agent_struct()
            if agent_struct is not None:
                mngr = self.gateway.get_gw_manager()
                mngr.update_user(agent_struct)
        except (GatewayFailedResult, GatewayNetworkError, ConnectionResetError) as e:
            print('ERROR:', e)
            return e
        except LogicError:
            pass

    def gw_add_self(self):
        """
        Will add this user to network access server
        :return: Nothing
        """
        if self.gateway is None:
            raise LogicError(_('gateway required'))
        try:
            agent_struct = self.build_agent_struct()
            if agent_struct is not None:
                mngr = self.gateway.get_gw_manager()
                mngr.add_user(agent_struct)
        except (GatewayFailedResult, GatewayNetworkError, ConnectionResetError) as e:
            print('ERROR:', e)
            return e
        except LogicError:
            pass

    def enable_service(self, service: Service, deadline=None, time_start=None):
        """
        Makes a services for current user, without money
        :param service: Instance of Service
        :param deadline: Time when service is expired
        :param time_start: Time when service has started
        :return: None
        """
        if deadline is None:
            deadline = service.calc_deadline()
        if time_start is None:
            time_start = datetime.now()
        self.current_service = CustomerService.objects.create(
            deadline=deadline, service=service,
            start_time=time_start
        )
        self.last_connected_service = service
        self.save(update_fields=('current_service', 'last_connected_service'))

    class Meta:
        db_table = 'customers'
        permissions = (
            ('can_buy_service', _('Buy service perm')),
            ('can_add_balance', _('fill account')),
            ('can_ping', _('Can ping'))
        )
        verbose_name = _('Customer')
        verbose_name_plural = _('Customers')
        ordering = ('fio',)
        unique_together = ('ip_address', 'gateway')


class PassportInfo(models.Model):
    series = models.CharField(
        _('Passport serial'),
        max_length=4,
        validators=(validators.integer_validator,)
    )
    number = models.CharField(
        _('Passport number'),
        max_length=6,
        validators=(validators.integer_validator,)
    )
    distributor = models.CharField(
        _('Distributor'),
        max_length=64
    )
    date_of_acceptance = models.DateField(_('Date of acceptance'))
    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )

    class Meta:
        db_table = 'passport_info'
        verbose_name = _('Passport Info')
        verbose_name_plural = _('Passport Info')
        ordering = ('series',)

    def __str__(self):
        return "%s %s" % (self.series, self.number)


class InvoiceForPayment(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)
    cost = models.FloatField(default=0.0)
    comment = models.CharField(max_length=128)
    date_create = models.DateTimeField(auto_now_add=True)
    date_pay = models.DateTimeField(blank=True, null=True)
    author = models.ForeignKey(
        UserProfile,
        related_name='+',
        on_delete=models.SET_NULL,
        blank=True,
        null=True
    )

    def __str__(self):
        return "%s -> %.2f" % (self.customer.username, self.cost)

    def set_ok(self):
        self.status = True
        self.date_pay = datetime.now()

    class Meta:
        ordering = ('date_create',)
        db_table = 'customer_inv_pay'
        verbose_name = _('Debt')
        verbose_name_plural = _('Debts')


class CustomerRawPassword(models.Model):
    customer = models.OneToOneField(Customer, models.CASCADE)
    passw_text = EncryptedCharField(max_length=64)

    def __str__(self):
        return "%s - %s" % (self.customer, self.passw_text)

    class Meta:
        db_table = 'customer_raw_password'


class AdditionalTelephone(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='additional_telephones'
    )
    telephone = models.CharField(
        max_length=16,
        verbose_name=_('Telephone'),
        # unique=True,
        validators=(RegexValidator(
            getattr(settings, 'TELEPHONE_REGEXP', r'^(\+[7893]\d{10,11})?$')
        ),)
    )
    owner_name = models.CharField(max_length=127)

    def __str__(self):
        return "%s - (%s)" % (self.owner_name, self.telephone)

    class Meta:
        db_table = 'additional_telephones'
        ordering = ('owner_name',)
        verbose_name = _('Additional telephone')
        verbose_name_plural = _('Additional telephones')


class PeriodicPayForId(models.Model):
    periodic_pay = models.ForeignKey(
        PeriodicPay,
        on_delete=models.CASCADE,
        verbose_name=_('Periodic pay')
    )
    last_pay = models.DateTimeField(_('Last pay time'), blank=True, null=True)
    next_pay = models.DateTimeField(_('Next time to pay'))
    account = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        verbose_name=_('Account')
    )

    def payment_for_service(self, author: UserProfile = None, now=None):
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
                account.add_balance(author, -amount, comment=gettext(
                    'Charge for "%(service)s"') % {
                        'service': self.periodic_pay
                    })
                account.save(update_fields=('balance',))
                self.last_pay = now
                self.next_pay = next_pay_date
                self.save(update_fields=('last_pay', 'next_pay'))

    def __str__(self):
        return "%s %s" % (self.periodic_pay, self.next_pay)

    class Meta:
        db_table = 'periodic_pay_for_id'
        ordering = ('last_pay',)


@receiver(post_init, sender=CustomerService)
def customer_service_post_init(sender, **kwargs):
    customer_service = kwargs["instance"]
    if getattr(customer_service, 'start_time') is None:
        customer_service.start_time = datetime.now()
    if getattr(customer_service, 'deadline') is None:
        calc_obj = customer_service.service.get_calc_type()(customer_service)
        customer_service.deadline = calc_obj.calc_deadline()


@receiver(pre_save, sender=CustomerService)
def customer_service_pre_save(sender, **kwargs):
    customer_service = kwargs["instance"]
    if getattr(customer_service, 'deadline') is None:
        calc_obj = customer_service.service.get_calc_type()(customer_service)
        customer_service.deadline = calc_obj.calc_deadline()
