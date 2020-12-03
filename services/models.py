from datetime import datetime

from django.contrib.postgres.fields import JSONField
from django.contrib.sites.models import Site
from django.core.validators import MinValueValidator
from django.db import models, connection
from django.utils.translation import gettext_lazy as _
from rest_framework.settings import api_settings

from djing2.models import BaseAbstractModel
from groupapp.models import Group
from services.custom_logic import (
    SERVICE_CHOICES, PERIODIC_PAY_CALC_DEFAULT,
    PERIODIC_PAY_CHOICES, ONE_SHOT_TYPES,
    ONE_SHOT_DEFAULT)
from services.custom_logic.base_intr import ServiceBase, PeriodicPayCalcBase, OneShotBaseService


class ServiceManager(models.Manager):
    def get_services_by_group(self, group_id):
        return self.filter(groups__id__in=group_id)


class Service(BaseAbstractModel):
    title = models.CharField(_('Service title'), max_length=128)
    descr = models.TextField(_('Service description'), null=True, blank=True, default=None)
    speed_in = models.FloatField(_('Speed in'), validators=[
        MinValueValidator(limit_value=0.1),
    ])
    speed_out = models.FloatField(_('Speed out'), validators=[
        MinValueValidator(limit_value=0.1),
    ])
    speed_burst = models.FloatField(
        _('Speed burst'),
        help_text=_('Result burst = speed * speed_burst,'
                    ' speed_burst must be >= 1.0'),
        default=1.0,
        validators=[
            MinValueValidator(limit_value=1.0),
        ]
    )
    cost = models.FloatField(
        verbose_name=_('Cost'),
        validators=[MinValueValidator(limit_value=0.0)]
    )
    calc_type = models.PositiveSmallIntegerField(_('Script'), choices=SERVICE_CHOICES)
    is_admin = models.BooleanField(_('Tech service'), default=False)
    groups = models.ManyToManyField(Group, blank=True, verbose_name=_('Groups'))
    sites = models.ManyToManyField(Site, blank=True)

    objects = ServiceManager()

    def calc_type_name(self):
        logic_class = self.get_calc_type()
        if hasattr(logic_class, 'description'):
            return getattr(logic_class, 'description')
        return str(logic_class)

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
        dtime_fmt = getattr(api_settings, 'DATETIME_FORMAT', '%Y-%m-%d %H:%M')
        return self.calc_deadline().strftime(dtime_fmt)

    @staticmethod
    def find_customer_service_by_device_credentials(dev_mac: str, dev_port: int):
        # TODO: make tests for it
        with connection.cursor() as cur:
            cur.execute("select * from find_customer_service_by_device_credentials(%s::macaddr, %s::smallint)",
                        [dev_mac, dev_port])
            res = cur.fetchone()
        if res is None or res[0] is None:
            return None
        pk, title, descr, speed_in, speed_out, cost, calc_type, is_admin, speed_burst, *other = res
        return Service(
            pk=pk,
            title=title,
            descr=descr,
            speed_in=float(speed_in),
            speed_out=float(speed_out),
            cost=float(cost),
            calc_type=calc_type,
            is_admin=is_admin,
            speed_burst=speed_burst
        )

    def __str__(self):
        return "%s (%.2f)" % (self.title, self.cost)

    class Meta:
        db_table = 'services'
        ordering = 'title',
        verbose_name = _('Service')
        verbose_name_plural = _('Services')
        unique_together = ('speed_in', 'speed_out', 'cost', 'calc_type')


class PeriodicPay(BaseAbstractModel):
    name = models.CharField(_('Periodic pay name'), max_length=64)
    when_add = models.DateTimeField(_('When pay created'), auto_now_add=True)
    calc_type = models.PositiveSmallIntegerField(
        verbose_name=_('Script type for calculations'),
        default=PERIODIC_PAY_CALC_DEFAULT, choices=PERIODIC_PAY_CHOICES
    )
    amount = models.FloatField(_('Total amount'))
    extra_info = JSONField(_('Extra info'), null=True, blank=True)
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
        ordering = '-id',


class OneShotPay(BaseAbstractModel):
    name = models.CharField(_('Shot pay name'), max_length=64)
    cost = models.FloatField(_('Total cost'))
    pay_type = models.PositiveSmallIntegerField(
        _('One shot pay type'),
        help_text=_('Uses for callbacks before pay and after pay'),
        choices=ONE_SHOT_TYPES,
        default=ONE_SHOT_DEFAULT
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
        ordering = 'name',
