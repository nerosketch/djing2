from django.conf import settings
from django.core import validators
from django.db import models
from django.utils.translation import gettext_lazy as _

from djing2.models import BaseAbstractModel
from dynamicfields.models import AbstractDynamicFieldContentModel
from profiles.models import BaseAccount
from groupapp.models import Group
from customers.models import Customer, CustomerStreet


class CustomerLegalModel(BaseAccount):
    group = models.ForeignKey(
        Group, on_delete=models.SET_NULL, blank=True, null=True, default=None, verbose_name=_("Legal customer group")
    )
    branches = models.ManyToManyField(Customer, blank=True, verbose_name=_('Branches'))
    balance = models.FloatField(default=0.0)
    street = models.ForeignKey(
        CustomerStreet, on_delete=models.SET_NULL, null=True, blank=True, default=None, verbose_name=_("Street")
    )
    title = models.CharField(_('Title'), max_length=256)
    house = models.CharField(_("House"), max_length=12, null=True, blank=True, default=None)

    description = models.TextField(_("Comment"), null=True, blank=True, default=None)

    # TODO: im not sure about this fields here
    # inn = models.CharField('ИНН', max_length=32, validators=[
    #     validators.integer_validator
    # ])
    # address_post_index = models.CharField(_('Address post index'), max_length=6, validators=[
    #     validators.integer_validator
    # ])
    # legal_office_addr = models.CharField(_('Legal office address'), max_length=32, validators=[
    #     validators.integer_validator
    # ])

    def get_telephones(self):
        return CustomerLegalTelephone.objects.filter(legal_customer=self).defer('legal_customer')

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'customers_legal'


class CustomerLegalTelephone(BaseAbstractModel):
    legal_customer = models.ForeignKey(CustomerLegalModel, on_delete=models.CASCADE)
    telephone = models.CharField(
        max_length=16,
        verbose_name=_("Telephone"),
        unique=True,
        validators=[validators.RegexValidator(getattr(settings, "TELEPHONE_REGEXP", r"^(\+[7893]\d{10,11})?$"))]
    )
    owner_name = models.CharField(max_length=127)
    create_time = models.DateTimeField(auto_now_add=True)
    last_change_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.owner_name} - ({self.telephone})"

    class Meta:
        db_table = "customer_legal_additional_telephones"


class CustomerLegalDynamicFieldContentModel(AbstractDynamicFieldContentModel):
    legal_customer = models.ForeignKey(CustomerLegalModel, on_delete=models.CASCADE)

    class Meta:
        db_table = 'customers_legal_dynamic_content'
