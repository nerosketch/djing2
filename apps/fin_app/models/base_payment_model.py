from django.utils.translation import gettext_lazy as _
from django.db import models
from django.contrib.sites.models import Site
from djing2.models import BaseAbstractModel
from customers.models import Customer


class BasePaymentModel(BaseAbstractModel):
    pay_system_title = "Base abstract implementation"

    title = models.CharField(_("Title"), max_length=64)
    slug = models.SlugField(_("Slug"), max_length=32, unique=True, allow_unicode=False)
    sites = models.ManyToManyField(Site, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = _("Base gateway")
        abstract = True


class BasePaymentLogModel(BaseAbstractModel):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_DEFAULT,
        blank=True, null=True, default=None
    )
    date_add = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(
        _("Cost"),
        default=0.0,
        max_digits=19,
        decimal_places=6
    )

    class Meta:
        verbose_name = _("Base payment log")
        abstract = True
