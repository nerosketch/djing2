from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core import validators
from django.db import models

from customers.models import Customer
from djing2.lib import safe_int
from groupapp.models import Group


def _float_validator(value: float):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValidationError(
            _("'%(value)s' value must be a float."),
            code='invalid',
            params={'value': value},
        )


class _DynamicField(models.CharField):
    description = _("Dynamic content field (up to %(max_length)s)")

    def get_prep_value(self, value):
        # python -> db
        return str(value) if value else 'null'

    @staticmethod
    def from_db_value(value, expression, connection):
        # db -> python
        return str(value) if value else None

    def clean(self, value, model_instance):
        type_validators = {
            1: validators.validate_integer,
            2: validators.validate_email,
            3: validators.validate_ipv4_address,
            4: _float_validator,
            5: validators.validate_slug
        }
        field_type = safe_int(model_instance.field_type)
        validator = type_validators.get(field_type)
        if validator is not None:
            self.validators.append(validator)
        return super().clean(value, model_instance)


class FieldModel(models.Model):
    title = models.CharField(_('Title'), max_length=80)
    FIELD_TYPES = (
        (0, _('Char Field')),
        (1, _('Integer Field')),
        (2, _('Email Field')),
        (3, _('Ip Field')),
        (4, _('Float Field')),
        (5, _('Slug Field')),
    )
    field_type = models.PositiveSmallIntegerField(_('Field type'), choices=FIELD_TYPES, default=0)
    groups = models.ManyToManyField(Group, related_name='fields', verbose_name=_('Groups'), db_table='dynamic_fields_groups')

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'dynamic_fields'
        ordering = ('title',)


# class FieldContentQuerySet(models.QuerySet):
#     def filter_for_customer(self, customer_id: int):
#         return self.filter(customer__id=customer_id)


class FieldContentModelManager(models.Manager):
    def fill_customer_account(self, customer: Customer):
        """
        If customer has no any field, then fill it with empty values
        """
        fcms = self.filter(customer=customer)
        fms = FieldModel.objects.filter(groups__in=customer.group).exclude(field_contents__in=fcms).iterator()
        self.bulk_create((FieldContentModel(
            customer=customer,
            content=None,
            field_type=fm
        ) for fm in fms), batch_size=100)


class FieldContentModel(models.Model):
    customer = models.ForeignKey(
        to=Customer, on_delete=models.CASCADE
    )
    content = _DynamicField(max_length=127, null=True, blank=True)
    field_type = models.ForeignKey(FieldModel, on_delete=models.CASCADE, related_name='field_contents')

    objects = FieldContentModelManager()

    class Meta:
        db_table = 'dynamic_field_content'
        unique_together = ('customer', 'field_type')
        # ordering = ('customer',)
