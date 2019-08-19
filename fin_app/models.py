from django.utils.translation import gettext_lazy as _
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField

from customers.models import Customer


class PayAllTimeGateway(models.Model):
    title = models.CharField(_('Title'), max_length=64)
    secret = EncryptedCharField(verbose_name=_('Secret'), max_length=64)
    service_id = models.CharField(_('Service id'), max_length=64)
    slug = models.SlugField(
        _('Slug'), max_length=32,
        unique=True, allow_unicode=False
    )

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'pay_all_time_gateways'
        verbose_name = _('All time gateway')
        ordering = 'title',


class AllTimePayLog(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_DEFAULT,
        blank=True,
        null=True,
        default=None
    )
    pay_id = models.CharField(
        max_length=36,
        unique=True,
        primary_key=True
    )
    date_add = models.DateTimeField(auto_now_add=True)
    sum = models.FloatField(_('Cost'), default=0.0)
    trade_point = models.CharField(
        _('Trade point'),
        max_length=20,
        default=None,
        null=True,
        blank=True
    )
    receipt_num = models.BigIntegerField(_('Receipt number'), default=0)
    pay_gw = models.ForeignKey(
        PayAllTimeGateway,
        verbose_name=_('Pay gateway'),
        on_delete=models.CASCADE
    )

    def __str__(self):
        return self.pay_id

    class Meta:
        db_table = 'all_time_pay_log'
        ordering = ('-date_add',)
