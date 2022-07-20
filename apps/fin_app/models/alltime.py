from django.db import models
from django.utils.translation import gettext_lazy as _
from encrypted_model_fields.fields import EncryptedCharField

from .base_payment_model import BasePaymentModel, BasePaymentLogModel


class AllTimePayGateway(BasePaymentModel):
    pay_system_title = "24 All Time"

    secret = EncryptedCharField(verbose_name=_("Secret"), max_length=64)
    service_id = models.CharField(_("Service id"), max_length=64)

    class Meta:
        db_table = "all_time_pay_gateways"
        verbose_name = _("All time gateway")


class AllTimePaymentLog(BasePaymentLogModel):
    pay_id = models.CharField(max_length=36, unique=True, primary_key=True)

    trade_point = models.CharField(
        _("Trade point"),
        max_length=20,
        default=None,
        null=True,
        blank=True
    )
    receipt_num = models.BigIntegerField(_("Receipt number"), default=0)

    def __str__(self):
        return self.pay_id

    class Meta:
        db_table = "all_time_payment_log"
