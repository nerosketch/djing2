from typing import Optional

from django.db import models, connection
from django.utils.translation import gettext as _
from djing2.models import BaseAbstractModel
from .interfaces import IAddressObject
from .fias_socrbase import AddressFIASInfo, AddressFIASLevelType


class AddressModelTypes(models.IntegerChoices):
    UNKNOWN = 0, _('Unknown')
    LOCALITY = 4, _('Locality')
    STREET = 8, _('Street')
    # HOUSE = 12, _('House')
    # BUILDING = 16, _('Building')
    OTHER = 64, _('Other')


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

    def filter_by_fias_level(self, level: AddressFIASLevelType):
        addr_type_ids_gen = AddressFIASInfo.get_address_types_by_level(level=level)
        addr_type_ids = [a.addr_code for a in addr_type_ids_gen]
        return self.filter(fias_address_type__in=addr_type_ids)

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


class AddressModelManager(models.Manager):
    @staticmethod
    def get_address_recursive_ids(addr_id: int, direction_down=True):
        query = (
            "WITH RECURSIVE chain(id, parent_addr_id) AS ("
                "SELECT id, parent_addr_id "
                "FROM addresses "
                "WHERE id = %s "
                "UNION "
                "SELECT a.id, a.parent_addr_id "
                "FROM chain c "
                "LEFT JOIN addresses a ON "
                f"{'a.parent_addr_id = c.id' if direction_down else 'a.id = c.parent_addr_id'}"
            ")"
            "SELECT id FROM chain WHERE id IS NOT NULL"
        )
        return models.expressions.RawSQL(sql=query, params=[addr_id])

    @staticmethod
    def get_address_full_title(addr_id: int) -> str:
        query = (
            "WITH RECURSIVE chain(id, parent_addr_id) AS ("
                "SELECT id, parent_addr_id, fias_address_type, title "
                "FROM addresses "
                "WHERE id = %s "
                "UNION "
                "SELECT a.id, a.parent_addr_id, a.fias_address_type, a.title "
                "FROM chain c "
                "LEFT JOIN addresses a ON "
                "a.id = c.parent_addr_id"
            ")"
            "SELECT id, fias_address_type, title FROM chain WHERE id IS NOT NULL"
        )
        addr_type_map = AddressFIASInfo.get_address_types_map()

        def _accumulate_addrs_hierarchy():
            with connection.cursor() as cur:
                cur.execute(query, (addr_id,))
                r = cur.fetchone()
                while r is not None:
                    r_addr_id, addr_type, title = r
                    addr = addr_type_map.get(addr_type)
                    type_code_short_title = addr.addr_short_name
                    yield r_addr_id, type_code_short_title, title
                    r = cur.fetchone()

        title_hierarchy = list(_accumulate_addrs_hierarchy())
        title_hierarchy.reverse()
        return ', '.join(f'{short_title}. {title}' for _, short_title, title in title_hierarchy)


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

    fias_address_level = models.CharField(
        _('Address Level'),
        max_length=8,
        choices=((str(num), name) for num, name in AddressFIASInfo.get_levels()),
        null=True, blank=True, default=None,
    )
    fias_address_type = models.IntegerField(
        _('FIAS address type'),
        choices=AddressFIASInfo.get_address_type_choices(),
        default=0
    )

    title = models.CharField(_('Title'), max_length=128)

    objects = AddressModelManager.from_queryset(AddressModelQuerySet)()

    def is_street(self):
        return self.address_type == AddressModelTypes.STREET

    def is_locality(self):
        return self.address_type == AddressModelTypes.LOCALITY

    def str_representation(self):
        return self.title

    def full_title(self):
        addr_id = int(self.pk)
        return AddressModelManager.get_address_full_title(
            addr_id=addr_id
        )

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
