from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.regex_helper import _lazy_re_compile
from django.utils.translation import gettext_lazy as _
from django.core import validators
from django.db import models

from djing2.lib import safe_int
from groupapp.models import Group


def _float_validator(value: float):
    try:
        return float(value)
    except (TypeError, ValueError) as err:
        raise ValidationError(
            _("'%(value)s' value must be a float."),
            code='invalid',
            params={'value': value},
        ) from err


class DynamicField(models.JSONField):
    description = _("Dynamic content field (up to %(max_length)s)")

    def clean(self, value, model_instance):
        type_validators = {
            1: validators.validate_integer,
            2: validators.validate_email,
            3: validators.validate_ipv4_address,
            4: _float_validator,
            5: validators.validate_slug
        }
        field = safe_int(model_instance.field)
        validator = type_validators.get(field)
        if validator is not None:
            self.validators.append(validator)
        return super().clean(value, model_instance)


class FieldModelTypeChoices(models.IntegerChoices):
    CHAR_FIELD = 0, _('Char Field')
    INTEGER_FIELD = 1, _('Integer Field')
    EMAIL_FIELD = 2, _('Email Field')
    IP_FIELD = 3, _('Ip Field')
    FLOAT_FIELD = 4, _('Float Field')
    SLUG_FIELD = 5, _('Slug Field')
    DATETIME_FIELD = 6, _('Datetime field')
    BOOLEAN_FIELD = 7, _('Boolean field')


class FieldModelTagChoices(models.IntegerChoices):
    DEFAULT = 0, _('Default tag')
    IPTV = 1, _('Uses IPTV')
    # POST_INDEX = 2, _('Post index')
    # CUSTOMER_BANK_TITLE = 3, _('Customer bank title')
    # CUSTOMER_BANK_ACCOUNT = 4, _('Customer bank account number')


validate_tags = RegexValidator(
    _lazy_re_compile(r'^(\w+\,?)+$'),
    _('Tags must contain only word characters (equivalent to [a-zA-Z0-9_]). And separated by comma.'),
    'invalid'
)


class FieldModel(models.Model):
    title = models.CharField(_('Title'), max_length=80)
    field_type = models.PositiveSmallIntegerField(
        _('Field type'),
        choices=FieldModelTypeChoices.choices,
        default=FieldModelTypeChoices.CHAR_FIELD
    )
    system_tag = models.PositiveSmallIntegerField(
        _('System tag'),
        choices=FieldModelTagChoices.choices,
        default=FieldModelTagChoices.DEFAULT
    )
    user_tag = models.CharField(
        _('User tag'),
        validators=[validate_tags],
        max_length=128,
        null=True,
        blank=True,
        default=None
    )
    groups = models.ManyToManyField(
        Group, related_name='fields',
        verbose_name=_('Groups'),
        db_table='dynamic_fields_groups'
    )

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'dynamic_fields'


# class FieldContentQuerySet(models.QuerySet):
#     def filter_for_customer(self, customer_id: int):
#         return self.filter(customer__id=customer_id)


# class FieldContentModelManager(models.Manager):
#     def fill_customer_account(self, customer: Customer):
#         """
#         If customer has no any field, then fill it with empty values
#         """
#         fcms = self.filter(customer=customer)
#         fms = FieldModel.objects.filter(groups__in=customer.group).exclude(field_contents__in=fcms).iterator()
#         self.bulk_create((FieldContentModel(
#             customer=customer,
#             content=None,
#             field=fm
#         ) for fm in fms), batch_size=100)


class AbstractDynamicFieldContentModel(models.Model):
    content = DynamicField(null=True, blank=True)
    field = models.ForeignKey(FieldModel, on_delete=models.CASCADE, related_name='+')

    # objects = FieldContentModelManager()

    class Meta:
        abstract = True
