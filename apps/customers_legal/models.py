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


class CustomerLegalIntegerChoices(models.IntegerChoices):
    NOT_CHOSEN = 0, _('Not chosen')
    LEGAL = 1, _('Legal customer')
    INDIVIDUAL = 2, _('Individual businessman')
    SELF_EMPLOYED = 3, _('Self employed')


class CustomerLegalModel(BaseAccount):
    group = models.ForeignKey(
        Group, on_delete=models.SET_NULL,
        blank=True, null=True, default=None,
        verbose_name=_("Legal customer group")
    )
    branches = models.ManyToManyField(
        Customer,
        blank=True,
        verbose_name=_('Branches')
    )
    balance = models.FloatField(default=0.0)

    # Юридический адрес
    address = models.ForeignKey(
        AddressModel,
        on_delete=models.SET_DEFAULT,
        related_name='legal_customer',
        null=True, blank=True, default=None,
        verbose_name=_("Legal address")
    )
    post_index = models.CharField(
        _('Post number'),
        help_text="почтовый индекс юридического адреса абонента",
        max_length=6,
        null=True, blank=True, default=None,
    )

    delivery_address = models.ForeignKey(
        to=AddressModel,
        related_name='delivery_customer_legal',
        on_delete=models.SET_DEFAULT,
        null=True, blank=True, default=None,
        verbose_name=_('Delivery address')
    )
    delivery_address_post_index = models.CharField(
        _('Delivery address post index'),
        max_length=6,
        null=True, blank=True, default=None,
    )

    # Post address info
    post_post_index = models.CharField(
        _('Post number'),
        max_length=6,
        null=True, blank=True, default=None,
    )
    post_address = models.ForeignKey(
        to=AddressModel,
        related_name='post_customer_legal',
        on_delete=models.SET_DEFAULT,
        null=True, blank=True, default=None,
        verbose_name=_('Address')
    )

    legal_type = models.PositiveSmallIntegerField(
        _('Legal type'),
        choices=CustomerLegalIntegerChoices.choices,
        default=CustomerLegalIntegerChoices.NOT_CHOSEN,
    )

    # ИНН, налоговый номер
    tax_number = models.CharField(
        _('Tax number'),
        unique=True,
        max_length=32,
        validators=[validators.integer_validator],
    )

    # ОГРН
    state_level_reg_number = models.CharField(
        _('State-level registration number'),
        max_length=64
    )

    # КПП при необходимости выставлять в динамическом поле

    actual_start_time = models.DateTimeField(
        _('Actual start time'),
        help_text="дата начала интервала, на котором актуальна информация",
    )
    actual_end_time = models.DateTimeField(
        _('Actual end time'),
        help_text="дата окончания интервала, на котором актуальна информация",
        null=True, blank=True, default=None,
    )

    title = models.CharField(
        _('Title'),
        max_length=256,
        unique=True
    )

    description = models.TextField(
        _("Comment"),
        null=True,
        blank=True,
        default=None
    )

    def get_telephones(self):
        return CustomerLegalTelephoneModel.objects.filter(
            legal_customer=self
        ).defer('legal_customer')

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'customers_legal'


class LegalCustomerBankModel(BaseAbstractModel):
    legal_customer = models.OneToOneField(
        to=CustomerLegalModel,
        on_delete=models.CASCADE,
    )
    title = models.CharField(
        _('Title'),
        help_text="Название банка",
        max_length=64,
    )
    bank_code = models.CharField(
        _('Bank identify code'),  # БИК
        max_length=64
    )
    correspondent_account = models.CharField(
        _('Correspondent account'),  # корреспондентский счёт
        max_length=64
    )
    settlement_account = models.CharField(
        _('Settlement account'),  # расчётный счёт
        max_length=64
    )

    class Meta:
        db_table = 'customer_legal_bank'


class CustomerLegalTelephoneModel(BaseAbstractModel):
    legal_customer = models.ForeignKey(CustomerLegalModel, on_delete=models.CASCADE)
    telephone = models.CharField(
        max_length=16,
        verbose_name=_("Telephone"),
        unique=True,
        validators=[validators.RegexValidator(
            getattr(settings, "TELEPHONE_REGEXP", r"^(\+[7893]\d{10,11})?$")
        )]
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
