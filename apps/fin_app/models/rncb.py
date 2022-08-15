from django.db import models
from django.utils.translation import gettext_lazy as _
from .base_payment_model import (
    BasePaymentModel,
    BasePaymentLogModel,
    add_payment_type
)


RNCB_DB_TYPE_ID = 2


class RNCBPaymentGatewayModelManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(payment_type=RNCB_DB_TYPE_ID)


class RNCBPaymentGateway(BasePaymentModel):
    pay_system_title = "RNCB"

    objects = RNCBPaymentGatewayModelManager()

    def save(self, *args, **kwargs):
        self.payment_type = RNCB_DB_TYPE_ID
        return super().save(*args, **kwargs)

    class Meta:
        #  db_table = "pay_rncb_gateways"
        verbose_name = _("RNCB gateway")
        proxy = True


class RNCBPaymentLog(BasePaymentLogModel):
    pay_id = models.IntegerField(unique=True)
    acct_time = models.DateTimeField(_('Act time from payment system'))

    def __str__(self):
        return str(self.pay_id)

    class Meta:
        db_table = "rncb_payment_log"


add_payment_type(RNCB_DB_TYPE_ID, RNCBPaymentGateway)
