from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver
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
        raise NotImplementedError

    def from_db_value(self, value, expression, connection):
        # db -> python
        raise NotImplementedError

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
    groups = models.ManyToManyField(Group, related_name='fields', verbose_name=_('Groups'))

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
        FieldContentModel.objects.bulk_create((FieldContentModel(
            customer=customer,
            content=None,
            field_type=fm
        ) for fm in fms), batch_size=100)


class FieldContentModel(models.Model):
    customer = models.OneToOneField(
        to=Customer, on_delete=models.CASCADE,
        primary_key=True
    )
    content = _DynamicField(max_length=127, null=True, blank=True)
    field_type = models.ForeignKey(FieldModel, on_delete=models.CASCADE, related_name='field_contents')

    objects = FieldContentModelManager()

    class Meta:
        db_table = 'dynamic_field_content'
        # ordering = ('customer',)


@receiver(post_save, sender=Customer)
def attach_dynamic_fields_to_new_customer(sender, instance: Customer, created: bool, **kwargs):
    if not created:
        return
    assert sender is Customer
    field_types = FieldModel.objects.filter(groups__in=instance.group).iterator()
    FieldContentModel.objects.bulk_create((FieldContentModel(
        customer=instance,
        content=None,
        field_type=ft
    ) for ft in field_types), batch_size=100)
