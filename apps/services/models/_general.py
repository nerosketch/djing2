from django.utils.translation import gettext_lazy as _
from djing2.lib import LogicError


class NotEnoughMoney(LogicError):
    default_detail = _("not enough money")
