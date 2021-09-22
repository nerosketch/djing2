from django.db import models
from django.contrib.sites.models import Site
from django.utils.translation import gettext_lazy as _
from djing2.models import BaseAbstractModel
from .interfaces import IAddressObject
from .fias_socrbase import AddressFIASInfo

#
# class LocalityModel(BaseAbstractModel):
#     title = models.CharField(_('Title'), max_length=127, unique=True)
#     sites = models.ManyToManyField(Site, blank=True)
#
#     def __str__(self):
#         return self.title
#
#     class Meta:
#         db_table = 'locality'
#
#
# class StreetModel(BaseAbstractModel):
#     name = models.CharField(_('Name'), max_length=64)
#     locality = models.ForeignKey(LocalityModel, on_delete=models.CASCADE)
#
#     def __str__(self):
#         return self.name
#
#     class Meta:
#         db_table = "locality_street"
#         verbose_name = _("Street")
#         verbose_name_plural = _("Streets")
#         unique_together = ('name', 'locality')


class AddressModelTypes(models.IntegerChoices):
    UNKNOWN = 0, _('Unknown')
    LOCALITY = 4, _('Locality')
    STREET = 8, _('Street')
    HOUSE = 12, _('House')
    BUILDING = 16, _('Building')


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

    fias_address_level = models.IntegerField(_('Address Level'), choices=((l, "Level %d" % l) for l in AddressFIASInfo.get_levels()))
    fias_address_type = models.IntegerField(
        _('FIAS address type'),
        choices=AddressFIASInfo.get_address_type_choices()
    )

    title = models.CharField(_('Title'), max_length=128)

    objects = AddressModelQuerySet.as_manager()

    def is_street(self):
        return self.ao_type == AddressModelTypes.STREET

    def is_locality(self):
        return self.address_type == AddressModelTypes.LOCALITY

    def str_representation(self):
        return self.title

    class Meta:
        db_table = 'addresses'
        unique_together = ('parent_addr', 'address_type', 'title')
