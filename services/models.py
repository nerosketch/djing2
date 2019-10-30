from datetime import datetime
from django.contrib.postgres.fields import JSONField
from django.core.validators import MinValueValidator
from django.db import models, IntegrityError
from django.utils.translation import gettext_lazy as _
from django.dispatch import receiver

from djing2.lib import MyChoicesAdapter
from services.base_intr import ServiceBase, PeriodicPayCalcBase
from services.custom_tariffs import TARIFF_CHOICES, PERIODIC_PAY_CHOICES
from groupapp.models import Group


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
    cost = models.FloatField(_('Cost'))
    calc_type = models.PositiveSmallIntegerField(_('Script'), choices=MyChoicesAdapter(TARIFF_CHOICES))
    is_admin = models.BooleanField(_('Tech service'), default=False)
    groups = models.ManyToManyField(Group, blank=True, verbose_name=_('Groups'))

    objects = ServiceManager()

    def get_calc_type(self):
        """
        :return: Child of services.base_intr.ServiceBase,
                 methods which provide the desired logic of payments
        """
        calc_code = self.calc_type
        for choice_pair in TARIFF_CHOICES:
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
        :return: subclass of custom_tariffs.PeriodicPayCalcBase with required
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


@receiver(models.signals.pre_delete, sender=PeriodicPay)
def periodic_pay_pre_delete(sender, **kwargs):
    raise IntegrityError('All linked abonapp.PeriodicPayForId will be removed, be careful')
