from django.db import models
from django.utils.translation import gettext_lazy as _

from dynamicfields.models import AbstractDynamicFieldContentModel
from profiles.models import BaseAccount
from groupapp.models import Group
from customers.models import Customer


class CustomerLegalModel(BaseAccount):
    title = models.CharField(_('Title'), max_length=256)
    group = models.ForeignKey(
        Group, on_delete=models.SET_NULL, blank=True, null=True, default=None, verbose_name=_("Legal customer group")
    )
    branches = models.ManyToManyField(Customer, blank=True, verbose_name=_('Branches'))
    balance = models.FloatField(default=0.0)
    description = models.TextField(_("Comment"), null=True, blank=True, default=None)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'customers_legal'


class CustomerLegalDynamicFieldContentModel(AbstractDynamicFieldContentModel):
    legal_customer = models.ForeignKey(CustomerLegalModel, on_delete=models.CASCADE)

    class Meta:
        db_table = 'customers_legal_dynamic_content'
