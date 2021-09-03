from django.utils.translation import gettext_lazy as _
from djing2.lib import safe_float
from .base_intr import OneShotBaseService


class ShotDefault(OneShotBaseService):
    description = _("Default shot pay logic")

    def calc_cost(self, model_object, request, customer) -> float:
        return safe_float(model_object.cost)

    def before_pay(self, request, customer):
        pass

    def after_pay(self, request, customer):
        pass
