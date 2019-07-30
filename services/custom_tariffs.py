from random import uniform
from datetime import timedelta, datetime
from calendar import monthrange

from django.utils import timezone
from django.utils.translation import gettext as _

from services.base_intr import ServiceBase, PeriodicPayCalcBase


class ServiceDefault(ServiceBase):
    description = _('Base calculate functionality')

    def __init__(self, customer_service):
        self.customer_service = customer_service

    # Базовый функционал считает стоимость пропорционально использованному времени
    def calc_cost(self) -> float:
        now = timezone.now()

        # сколько прошло с начала действия услуги
        # если времени начала нет то это начало действия, использованное время 0
        time_diff = now - self.customer_service.time_start if self.customer_service.time_start else timedelta(0)

        # времени в этом месяце
        curr_month_time = datetime(now.year, now.month if now.month == 12 else now.month + 1, 1) - timedelta(days=1)
        curr_month_time = timedelta(days=curr_month_time.day)

        # Сколько это в процентах от всего месяца (k - коеффициент)
        k = time_diff.total_seconds() / curr_month_time.total_seconds()

        # результат - это полная стоимость тарифа умноженная на k
        res = k * self.customer_service.service.amount

        return float(res)

    # Тут мы расчитываем конец действия услуги, завершение будет в конце месяца
    def calc_deadline(self) -> datetime:
        now = timezone.now()
        last_day = monthrange(now.year, now.month)[1]
        last_month_date = datetime(
            year=now.year, month=now.month,
            day=last_day, hour=23,
            minute=59, second=59
        )
        return last_month_date


class TariffDp(ServiceDefault):
    description = 'IS'
    # в IS снимается вся стоимость тарифа вне зависимости от времени использования

    # просто возвращаем всю стоимость тарифа
    def calc_cost(self) -> float:
        return float(self.customer_service.service.cost)


# Как в IS только не на время, а на 10 лет
class TariffCp(TariffDp):
    description = _('Private service')

    def calc_deadline(self) -> datetime:
        # делаем время окончания услуги на 10 лет вперёд
        now = timezone.now()
        long_long_time = datetime(
            year=now.year + 10, month=now.month,
            day=now.day, hour=23,
            minute=59, second=59
        )
        return long_long_time


# Daily service
class TariffDaily(TariffDp):
    description = _('IS Daily service')

    def calc_deadline(self):
        now = timezone.now()
        # next day in the same time
        one_day = timedelta(days=1)
        return now + one_day


# Первый - всегда по умолчанию
TARIFF_CHOICES = (
    (0, ServiceDefault),
    (1, TariffDp),
    (2, TariffCp),
    (3, TariffDaily)
)


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


PERIODIC_PAY_CHOICES = (
    (0, PeriodicPayCalcDefault),
    (1, PeriodicPayCalcRandom)
)
