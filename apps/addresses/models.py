from typing import Optional

from django.db import models
from django.contrib.sites.models import Site
from django.utils.translation import gettext as _
from djing2.models import BaseAbstractModel
from .interfaces import IAddressObject
from .fias_socrbase import AddressFIASInfo


class AddressModelTypes(models.IntegerChoices):
    UNKNOWN = 0, _('Unknown')
    LOCALITY = 4, _('Locality')
    STREET = 8, _('Street')
    # HOUSE = 12, _('House')
    # BUILDING = 16, _('Building')


class AddressModelQuerySet(models.QuerySet):
    def filter_streets(self, locality_id: Optional[int] = None):
        qs = self.filter(address_type=AddressModelTypes.STREET)
        if locality_id is not None:
            return qs.filter(
                parent_addr__address_type=AddressModelTypes.LOCALITY,
                parent_addr__id=locality_id
            )
        return qs

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


AddressFIASLevelChoices = tuple((level, "Level %d" % level) for level in AddressFIASInfo.get_levels())


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

    fias_address_level = models.IntegerField(
        _('Address Level'),
        choices=AddressFIASLevelChoices,
        default=0
    )
    fias_address_type = models.IntegerField(
        _('FIAS address type'),
        choices=AddressFIASInfo.get_address_type_choices(),
        default=0
    )

    title = models.CharField(_('Title'), max_length=128)

    objects = AddressModelQuerySet.as_manager()

    def is_street(self):
        return self.address_type == AddressModelTypes.STREET

    def is_locality(self):
        return self.address_type == AddressModelTypes.LOCALITY

    def str_representation(self):
        return self.title

    # @staticmethod
    # def get_streets_as_addr_objects():
    #     with connection.cursor() as cur:
    #         cur.execute(
    #             "SELECT cs.id AS street_id,"
    #             "sa.id        AS parent_ao_id,"
    #             "sa.ao_type   AS parent_ao_type,"
    #             "cs.name      AS street_name "
    #             "FROM locality_street cs "
    #             "JOIN sorm_address sa ON cs.locality_id = sa.locality_id;"
    #         )
    #         res = cur.fetchone()
    #         while res is not None:
    #             # res: street_id, parent_ao_id, parent_ao_type, street_name
    #             yield res
    #             res = cur.fetchone()

    class Meta:
        db_table = 'addresses'
        unique_together = ('parent_addr', 'address_type', 'title')
