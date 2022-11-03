from typing import Optional
from datetime import timedelta, datetime
from calendar import monthrange

from django.utils import timezone
from django.utils.translation import gettext as _

from services.custom_logic.base_intr import ServiceBase


def get_month_max_time(now: Optional[datetime] = None) -> timedelta:
    week_day, n_days = monthrange(now.year, now.month)
    curr_month_time = timedelta(days=n_days)
    return curr_month_time


class ServiceDefault(ServiceBase):
    description = _("Base calculate functionality")

    def __init__(self, customer_service):
        self.customer_service = customer_service

    def get_how_long_time_used(self, now: Optional[datetime] = None) -> timedelta:
        # сколько прошло с начала действия услуги
        # если времени начала нет то это начало действия, использованное время 0
        if now is None:
            now = datetime.now()
        if self.customer_service.start_time:
            time_used = now - self.customer_service.start_time
        else:
            time_used = timedelta(0)
        return time_used

    def calc_cost(self) -> float:
        """Базовый функционал считает стоимость пропорционально использованному времени."""

        now = timezone.now()
        how_long_use = self.get_how_long_time_used(now=now)
        curr_month_all_time = get_month_max_time(now=now)
        use_coefficient = how_long_use.total_seconds() / curr_month_all_time.total_seconds()
        used_cost = use_coefficient * self.customer_service.service.cost
        return float(used_cost)

    def calc_deadline(self) -> datetime:
        """Тут мы расчитываем конец действия услуги, завершение будет в конце месяца."""

        # FIXME: service has no start_time
        start_time = self.customer_service.start_time

        if start_time.month == 12:
            last_month_date = datetime(
                year=start_time.year+1,
                month=1,
                day=1
            )
        else:
            last_month_date = datetime(
                year=start_time.year,
                month=start_time.month+1,
                day=1
            )
        return last_month_date


class TariffDp(ServiceDefault):
    description = "IS"
    # в IS снимается вся стоимость тарифа вне зависимости от времени использования

    # просто возвращаем всю стоимость тарифа
    def calc_cost(self) -> float:
        return float(self.customer_service.service.cost)


# Как в IS только не на время, а на 10 лет
class TariffCp(TariffDp):
    description = _("Private service")

    def calc_deadline(self) -> datetime:
        now = timezone.now()
        ten_years = datetime(
            year=now.year + 10,
            month=now.month,
            day=1,
            hour=23,
            minute=59,
            second=59
        )
        return ten_years


# Daily service
class TariffDaily(TariffDp):
    description = _("IS Daily service")

    def calc_deadline(self):
        now = timezone.now()
        # next day in the same time
        one_day = timedelta(days=1)
        return now + one_day
