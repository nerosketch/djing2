from decimal import Decimal
from typing import Optional
from datetime import datetime
from django.contrib.sites.models import Site
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from djing2.models import BaseAbstractModel
from customers.models import Customer
from profiles.models import UserProfile
from services.custom_logic.base_intr import PeriodicPayCalcBase
from services.custom_logic import (
    PERIODIC_PAY_CALC_DEFAULT,
    PERIODIC_PAY_CHOICES,
)


class PeriodicPayForId(BaseAbstractModel):
    periodic_pay = models.ForeignKey(
        'PeriodicPay',
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
