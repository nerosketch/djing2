from django.db import models
from django.contrib.sites.models import Site
from django.utils.translation import gettext_lazy as _
from djing2.models import BaseAbstractModel
from .interfaces import IAddressObject


class AddressModelTypes(models.IntegerChoices):
    UNKNOWN = 0, _('Unknown')
    LOCALITY = 4, _('Locality')
    STREET = 8, _('Street')
    # HOUSE = 12, _('House')
    # BUILDING = 16, _('Building')


class AddressModelQuerySet(models.QuerySet):
    def filter_streets(self):
        return self.filter(address_type=AddressModelTypes.STREET)

    def filter_localities(self):
        return self.filter(address_type=AddressModelTypes.LOCALITY)

    def filter_unknown(self):
        return self.filter(address_type=AddressModelTypes.UNKNOWN)

    def create_street(self, **kwargs):
        del kwargs['address_type']
        return self.create(
            address_type=AddressModelTypes.STREET,
            **kwargs
        )

    def create_locality(self, **kwargs):
        del kwargs['address_type']
        return self.create(
            address_type=AddressModelTypes.LOCALITY,
            **kwargs
        )


class AddressModel(IAddressObject, BaseAbstractModel):
    parent_addr = models.ForeignKey(
        'self', verbose_name=_('Parent address'),
        on_delete=models.SET_DEFAULT,
        null=True,
        blank=True,
        default=None
    )
    address_type = models.PositiveSmallIntegerField(
        verbose_name=_('Address type'),
        choices=AddressModelTypes.choices,
        default=AddressModelTypes.UNKNOWN
    )

    title = models.CharField(_('Title'), max_length=128)

    objects = AddressModelQuerySet.as_manager()

    def is_street(self):
        return self.address_type == AddressModelTypes.STREET

    def is_locality(self):
        return self.address_type == AddressModelTypes.LOCALITY

    def str_representation(self):
        return self.title

    class Meta:
        db_table = 'addresses'
        unique_together = ('parent_addr', 'address_type', 'title')
