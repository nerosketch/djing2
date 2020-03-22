from .periodic import PeriodicPayCalcDefault, PeriodicPayCalcRandom
from .services import ServiceDefault, TariffDp, TariffCp, TariffDaily
from .oneshot import ShotDefault

# First - already default
SERVICE_CHOICE_DEFAULT = 0
SERVICE_CHOICE_DP = 1
SERVICE_CHOICE_CP = 2
SERVICE_CHOICE_DAILY = 3

SERVICE_CHOICES = (
    (SERVICE_CHOICE_DEFAULT, ServiceDefault),
    (SERVICE_CHOICE_DP, TariffDp),
    (SERVICE_CHOICE_CP, TariffCp),
    (SERVICE_CHOICE_DAILY, TariffDaily)
)


PERIODIC_PAY_CHOICES = (
    (0, PeriodicPayCalcDefault),
    (1, PeriodicPayCalcRandom)
)

ONE_SHOT_TYPES = (
    (0, ShotDefault),
)

__all__ = ('SERVICE_CHOICES', 'SERVICE_CHOICE_DEFAULT', 'SERVICE_CHOICE_DP',
           'SERVICE_CHOICE_CP', 'SERVICE_CHOICE_DAILY',
           'PERIODIC_PAY_CHOICES', 'ONE_SHOT_TYPES')
