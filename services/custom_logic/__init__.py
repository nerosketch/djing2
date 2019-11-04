from .periodic import *
from .services import *
from .oneshot import *

# Первый - всегда по умолчанию
SERVICE_CHOICES = (
    (0, ServiceDefault),
    (1, TariffDp),
    (2, TariffCp),
    (3, TariffDaily)
)


PERIODIC_PAY_CHOICES = (
    (0, PeriodicPayCalcDefault),
    (1, PeriodicPayCalcRandom)
)

ONE_SHOT_TYPES = (
    (0, ShotDefault),
)

__all__ = ('SERVICE_CHOICES', 'PERIODIC_PAY_CHOICES', 'ONE_SHOT_TYPES')
