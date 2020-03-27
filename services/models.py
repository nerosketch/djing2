from datetime import datetime
from ipaddress import IPv4Address, AddressValueError
from django.contrib.postgres.fields import JSONField
from django.core.validators import MinValueValidator
from django.db import models, IntegrityError, connection
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from netaddr import EUI
from djing2.lib import MyChoicesAdapter
from groupapp.models import Group
from services.custom_logic import *
from services.custom_logic.base_intr import ServiceBase, PeriodicPayCalcBase, OneShotBaseService


class ServiceManager(models.Manager):
    def get_services_by_group(self, group_id):
        return self.filter(groups__id__in=group_id)


class Service(models.Model):
    title = models.CharField(_('Service title'), max_length=128)
    descr = models.TextField(_('Service description'), null=True, blank=True, default=None)
    speed_in = models.FloatField(_('Speed in'), validators=(
        MinValueValidator(limit_value=0.1),
    ))
    speed_out = models.FloatField(_('Speed out'), validators=(
        MinValueValidator(limit_value=0.1),
    ))
    speed_burst = models.FloatField(
        _('Speed burst'),
        help_text=_('Result burst = speed * speed_burst,'
                    ' speed_burst must be > 1.0'),
        default=1.0,
        validators=(
            MinValueValidator(limit_value=1.0),
        )
    )
    cost = models.FloatField(_('Cost'))
    calc_type = models.PositiveSmallIntegerField(_('Script'), choices=MyChoicesAdapter(SERVICE_CHOICES))
    is_admin = models.BooleanField(_('Tech service'), default=False)
    groups = models.ManyToManyField(Group, blank=True, verbose_name=_('Groups'))

    objects = ServiceManager()

    def get_calc_type(self):
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

    def calc_deadline(self):
        calc_type = self.get_calc_type()
        calc_obj = calc_type(self)
        return calc_obj.calc_deadline()

    def calc_deadline_formatted(self):
        return self.calc_deadline().strftime('%Y-%m-%dT%H:%M')

    @staticmethod
    def get_user_credentials_by_ip(ip_addr: str):
        try:
            ip_addr = IPv4Address(ip_addr)
        except AddressValueError:
            return None
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM find_customer_service_by_ip(%s::inet)",
                        (str(ip_addr),))
            res = cur.fetchone()
        f_id, f_title, f_descr, f_speed_in, f_speed_out, f_cost, f_calc_type, f_is_admin, f_speed_burst = res
        if f_id is None:
            return None
        return Service(
            pk=f_id, title=f_title, descr=f_descr, speed_in=f_speed_in,
            speed_out=f_speed_out, cost=f_cost, calc_type=f_calc_type,
            is_admin=f_is_admin, speed_burst=f_speed_burst
        )

    @staticmethod
    def get_user_credentials_by_device_onu(device_mac_addr: str):
        device_mac_addr = str(EUI(device_mac_addr))
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM find_customer_service_by_device_onu_credentials(%s::macaddr)",
                        [device_mac_addr])
            res = cur.fetchone()
        f_id, f_title, f_descr, f_speed_in, f_speed_out, f_cost, f_calc_type, f_is_admin, f_speed_burst = res
        if f_id is None:
            return None
        return Service(
            pk=f_id, title=f_title, descr=f_descr, speed_in=f_speed_in,
            speed_out=f_speed_out, cost=f_cost, calc_type=f_calc_type,
            is_admin=f_is_admin, speed_burst=f_speed_burst
        )

    def __str__(self):
        return "%s (%.2f)" % (self.title, self.cost)

    class Meta:
        db_table = 'services'
        ordering = ('title',)
        verbose_name = _('Service')
        verbose_name_plural = _('Services')
        unique_together = ('speed_in', 'speed_out', 'cost', 'calc_type')


class PeriodicPay(models.Model):
    name = models.CharField(_('Periodic pay name'), max_length=64)
    when_add = models.DateTimeField(_('When pay created'), auto_now_add=True)
    calc_type = models.PositiveSmallIntegerField(
        verbose_name=_('Script type for calculations'),
        default=0, choices=MyChoicesAdapter(PERIODIC_PAY_CHOICES)
    )
    amount = models.FloatField(_('Total amount'))
    extra_info = JSONField(_('Extra info'), null=True, blank=True)

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

    class Meta:
        db_table = 'periodic_pay'
        verbose_name = _('Periodic pay')
        verbose_name_plural = _('Periodic pays')
        ordering = ('-id',)


class OneShotPay(models.Model):
    name = models.CharField(_('Shot pay name'), max_length=64)
    cost = models.FloatField(_('Total cost'))
    pay_type = models.PositiveSmallIntegerField(
        _('One shot pay type'),
        help_text=_('Uses for callbacks before pay and after pay'),
        choices=MyChoicesAdapter(ONE_SHOT_TYPES),
        default=0
    )
    _pay_type_cache = None

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

    def before_pay(self, request, customer):
        pay_logic = self._get_calc_object()
        pay_logic.before_pay(request, customer)

    def calc_cost(self, request, customer) -> float:
        pay_logic = self._get_calc_object()
        return pay_logic.calc_cost(self, request, customer)

    def after_pay(self, request, customer):
        pay_logic = self._get_calc_object()
        pay_logic.before_pay(request, customer)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'service_one_shot'
        ordering = ('name',)


@receiver(models.signals.pre_delete, sender=PeriodicPay)
def periodic_pay_pre_delete(sender, **kwargs):
    raise IntegrityError('All linked abonapp.PeriodicPayForId will be removed, be careful')
