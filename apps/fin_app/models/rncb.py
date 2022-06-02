from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.sites.models import Site
from djing2.models import BaseAbstractModel
from customers.models import Customer


class PayRNCBGateway(BaseAbstractModel):
    pay_system_title = "RNCB"

    title = models.CharField(_("Title"), max_length=64)
    slug = models.SlugField(_("Slug"), max_length=32, unique=True, allow_unicode=False)
    sites = models.ManyToManyField(Site, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "pay_rncb_gateways"
        verbose_name = _("RNCB gateway")


class RNCBPayLog(BaseAbstractModel):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_DEFAULT,
        blank=True, null=True, default=None
    )
    pay_id = models.IntegerField(unique=True)
    date_add = models.DateTimeField(auto_now_add=True)
    acct_time = models.DateTimeField(_('Act time from paument system'))
    amount = models.DecimalField(
        _("Cost"),
        default=0.0,
        max_digits=19,
        decimal_places=6
    )
    pay_gw = models.ForeignKey(
        PayRNCBGateway,
        verbose_name=_("Pay gateway"),
        on_delete=models.CASCADE
    )

    def __str__(self):
        return self.pay_id

    class Meta:
        db_table = "rncb_pay_log"
