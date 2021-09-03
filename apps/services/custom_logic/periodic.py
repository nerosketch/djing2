from calendar import monthrange
from random import uniform
from datetime import timedelta, datetime, date

from django.utils.translation import gettext as _

from services.custom_logic.base_intr import PeriodicPayCalcBase


class PeriodicPayCalcDefault(PeriodicPayCalcBase):
    description = _("Default periodic pay")

    def calc_amount(self, model_object) -> float:
        return model_object.amount

    def get_next_time_to_pay(self, model_object, last_time_payment) -> datetime:
        today = date.today()
        nw = datetime(today.year, today.month, today.day)
        days = monthrange(nw.year, nw.month)[1]
        return nw + timedelta(days - nw.day + 1)


class PeriodicPayCalcRandom(PeriodicPayCalcDefault):
    description = _("Random periodic pay")

    def calc_amount(self, model_object) -> float:
        """
        :param model_object: it is a instance of models.PeriodicPay model
        :return: float: amount for the service
        """
        return uniform(1, 10)
