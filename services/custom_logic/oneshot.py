from django.utils.translation import gettext_lazy as _
from djing2.lib import safe_float
from .base_intr import OneShotBaseService


class ShotDefault(OneShotBaseService):
    description = _('Default shot pay logic')

    def calc_amount(self, model_object) -> float:
        return safe_float(model_object.cost)

    def before_pay(self):
        pass

    def after_pay(self):
        pass
