from decimal import Decimal
from django.contrib.sites.models import Site
from django.db import models
from django.utils.translation import gettext_lazy as _

from customers.models import Customer
from djing2.models import BaseAbstractModel
from profiles.models import UserProfile
from services.custom_logic import (
    ONE_SHOT_TYPES,
    ONE_SHOT_DEFAULT,
)
from services.custom_logic.base_intr import OneShotBaseService
from ._general import NotEnoughMoney


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
