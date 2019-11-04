from random import uniform
from datetime import timedelta, datetime

from django.utils.translation import gettext as _

from services.custom_logic.base_intr import PeriodicPayCalcBase


class PeriodicPayCalcDefault(PeriodicPayCalcBase):
    description = _('Default periodic pay')

    def calc_amount(self, model_object) -> float:
        return model_object.amount

    def get_next_time_to_pay(self, model_object, last_time_payment) -> datetime:
        # TODO: решить какой будет расёт периодических платежей
        return datetime.now() + timedelta(days=30)


class PeriodicPayCalcRandom(PeriodicPayCalcDefault):
    description = _('Random periodic pay')

    def calc_amount(self, model_object) -> float:
        """
        :param model_object: it is a instance of models.PeriodicPay model
        :return: float: amount for the service
        """
        return uniform(1, 10)
