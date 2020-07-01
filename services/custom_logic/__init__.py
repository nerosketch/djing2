from django.db.models import IntegerChoices
from .periodic import PeriodicPayCalcDefault, PeriodicPayCalcRandom
from .services import ServiceDefault, TariffDp, TariffCp, TariffDaily
from .oneshot import ShotDefault


class SERVICE_CHOICES(IntegerChoices):
    # First - already default
    SERVICE_CHOICE_DEFAULT = 0, ServiceDefault.description
    SERVICE_CHOICE_DP = 1, TariffDp.description
    SERVICE_CHOICE_CP = 2, TariffCp.description
    SERVICE_CHOICE_DAILY = 3, TariffDaily.description


class PERIODIC_PAY_CHOICES(IntegerChoices):
    PERIODIC_PAY_CALC_DEFAULT = 0, PeriodicPayCalcDefault.description
    PERIODIC_PAY_CALC_RANDOM = 1, PeriodicPayCalcRandom.description


class ONE_SHOT_TYPES(IntegerChoices):
    ONE_SHOT_DEFAULT = 0, ShotDefault.description


__all__ = ('SERVICE_CHOICES',
           'PERIODIC_PAY_CHOICES', 'ONE_SHOT_TYPES')
