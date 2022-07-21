from django.db import models
from django.utils.translation import gettext_lazy as _
from encrypted_model_fields.fields import EncryptedCharField

from .base_payment_model import (
    BasePaymentModel,
    BasePaymentLogModel,
    add_payment_type
)

ALLTIME_DB_TYPE_ID = 3


class AllTimePayGatewayModelManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(payment_type=ALLTIME_DB_TYPE_ID)


class AllTimePayGateway(BasePaymentModel):
    pay_system_title = "24 All Time"

    secret = EncryptedCharField(verbose_name=_("Secret"), max_length=64)
    service_id = models.CharField(_("Service id"), max_length=64)

    objects = AllTimePayGatewayModelManager()

    def save(self, *args, **kwargs):
        self.payment_type = ALLTIME_DB_TYPE_ID
        return super().save(*args, **kwargs)

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


add_payment_type(ALLTIME_DB_TYPE_ID, AllTimePayGateway)
