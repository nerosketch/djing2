from django.db import models
from django.utils.translation import gettext_lazy as _
from .base_payment_model import BasePaymentModel, BasePaymentLogModel


class PayRNCBGateway(BasePaymentModel):
    pay_system_title = "RNCB"

    class Meta:
        db_table = "pay_rncb_gateways"
        verbose_name = _("RNCB gateway")


class RNCBPayLog(BasePaymentLogModel):
    pay_id = models.IntegerField(unique=True)
    acct_time = models.DateTimeField(_('Act time from payment system'))
    pay_gw = models.ForeignKey(
        PayRNCBGateway,
        verbose_name=_("Pay gateway"),
        on_delete=models.CASCADE
    )

    def __str__(self):
        return str(self.pay_id)

    class Meta:
        db_table = "rncb_pay_log"
