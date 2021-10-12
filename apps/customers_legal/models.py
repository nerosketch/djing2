from django.conf import settings
from django.core import validators
from django.db import models
from django.utils.translation import gettext_lazy as _

from djing2.models import BaseAbstractModel
from addresses.models import AddressModel
from dynamicfields.models import AbstractDynamicFieldContentModel
from profiles.models import BaseAccount
from groupapp.models import Group
from customers.models import Customer


class CustomerLegalModel(BaseAccount):
    group = models.ForeignKey(
        Group, on_delete=models.SET_NULL, blank=True, null=True, default=None, verbose_name=_("Legal customer group")
    )
    branches = models.ManyToManyField(Customer, blank=True, verbose_name=_('Branches'))
    balance = models.FloatField(default=0.0)
    address = models.ForeignKey(
        AddressModel,
        on_delete=models.SET_DEFAULT,
        null=True, blank=True, default=None,
        verbose_name=_("Address")
    )

    # ИНН, налоговый номер
    tax_number = models.CharField(
        _('Tax number'),
        max_length=32,
        validators=validators.integer_validator,
    )

    post_index = models.CharField(
        _('Post number'),
        help_text="почтовый индекс адреса абонента",
        max_length=32,
        null=True, blank=True, default=None,
    )

    legal_address = models.ForeignKey(
        to=AddressModel,
        verbose_name=_('Legal address'),
        on_delete=models.SET_DEFAULT,
        null=True, blank=True, default=None,
    )

    actual_start_time = models.DateTimeField(
        _('Actual start time'),
        help_text="дата начала интервала, на котором актуальна информация",
    )
    actual_end_time = models.DateTimeField(
        _('Actual end time'),
        help_text="дата окончания интервала, на котором актуальна информация",
        null=True, blank=True, default=None,
    )

    title = models.CharField(_('Title'), max_length=256)

    description = models.TextField(_("Comment"), null=True, blank=True, default=None)

    def get_telephones(self):
        return CustomerLegalTelephone.objects.filter(legal_customer=self).defer('legal_customer')

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'customers_legal'


class LegalCustomerBank(BaseAbstractModel):
    legal_customer = models.OneToOneField(
        to=CustomerLegalModel,
        on_delete=models.CASCADE,
    )
    title = models.CharField(
        _('Title'),
        max_length=64,
    )
    post_index = models.CharField(
        _('Post number'),
        help_text="Почтовый индекс почтового адреса абонента",
        max_length=32,
        null=True, blank=True, default=None,
    )
    number = models.CharField(
        _('Bank account number'),
        max_length=64
    )

    class Meta:
        db_table = 'customer_legal_bank'


class LegalCustomerPostAddressInfo(BaseAbstractModel):
    legal_customer = models.ForeignKey(
        to=CustomerLegalModel,
        on_delete=models.CASCADE,
    )
    post_index = models.CharField(
        _('Post number'),
        max_length=32,
        null=True, blank=True, default=None,
    )
    office_num = models.CharField(
        _('Office number'),
        max_length=32,
    )
    address = models.ForeignKey(
        to=AddressModel,
        on_delete=models.CASCADE,
        verbose_name=_('Address')
    )

    class Meta:
        db_table = 'customer_legal_post_address'


class LegalCustomerDeliveryAddress(BaseAbstractModel):
    legal_customer = models.ForeignKey(
        to=CustomerLegalModel,
        on_delete=models.CASCADE,
    )
    address = models.ForeignKey(
        to=AddressModel,
        on_delete=models.CASCADE,
        verbose_name=_('Address')
    )

    class Meta:
        db_table = 'customer_legal_delivery_address'


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
