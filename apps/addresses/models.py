from __future__ import annotations
from typing import Optional
from django.db import models, connection
from django.db.models import Q, Count
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from djing2.lib import safe_int, IntEnumEx
from djing2.models import BaseAbstractModel
from .interfaces import IAddressObject
from .fias_socrbase import AddressFIASInfo, AddressFIASLevelType


class AddressModelTypes(IntEnumEx):
    UNKNOWN = 0, _('Unknown')
    LOCALITY = 4, _('Locality')
    STREET = 8, _('Street')
    HOUSE = 12, _('House')
    OFFICE_NUM = 16, _('Office number')
    BUILDING = 20, _('Building')
    CORPUS = 24, 'Корпус'
    OTHER = 64, _('Other')


class AddressModelQuerySet(models.QuerySet):
    def filter_from_parent(self, addr_type: AddressModelTypes, *,
                           parent_id: Optional[int] = None,
                           parent_type: Optional[AddressModelTypes] = None):
        """Filters all children addresses of parent_id, with optional specified type and id."""
        qs = self.filter(address_type=addr_type)
        if parent_id is not None:
            qs = qs.filter(
                parent_addr_id=parent_id
            )
        if parent_type is not None:
            qs = qs.filter(
                parent_addr__address_type=parent_type,
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
            "    SELECT id, parent_addr_id "
            "    FROM addresses "
            "    WHERE id = %s "
            "    UNION "
            "    SELECT a.id, a.parent_addr_id "
            "    FROM chain c "
            "    LEFT JOIN addresses a ON "
            f"   {'a.parent_addr_id = c.id' if direction_down else 'a.id = c.parent_addr_id'}"
            ")"
            "SELECT id FROM chain WHERE id IS NOT NULL"
        )
        return models.expressions.RawSQL(sql=query, params=[addr_id])

    def get_address_by_type(self, addr_id: int, addr_type: AddressModelTypes):
        ids_tree_query = AddressModelManager.get_address_recursive_ids(
            addr_id=addr_id,
            direction_down=False
        )
        return self.filter(pk__in=ids_tree_query, address_type=addr_type)

    @staticmethod
    def get_address_full_title(addr_id: int) -> str:
        query = (
            "WITH RECURSIVE chain(id, parent_addr_id) AS ("
            "    SELECT id, parent_addr_id, fias_address_type, title "
            "    FROM addresses "
            "    WHERE id = %s "
            "    UNION "
            "    SELECT a.id, a.parent_addr_id, a.fias_address_type, a.title "
            "    FROM chain c "
            "    LEFT JOIN addresses a ON a.id = c.parent_addr_id"
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
                    if addr is None:
                        raise ValueError('address type %d does not have a corresponding address object' % addr_type)
                    type_code_short_title = addr.addr_short_name
                    yield r_addr_id, type_code_short_title, title
                    r = cur.fetchone()

        title_hierarchy = list(_accumulate_addrs_hierarchy())
        title_hierarchy.reverse()
        return ', '.join('%s %s' % (short_title, title) for _, short_title, title in title_hierarchy)


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
        default=AddressModelTypes.UNKNOWN.value
    )
    fias_address_level = models.IntegerField(
        _('Address Level'),
        choices=((num, name) for num, name in AddressFIASInfo.get_levels()),
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
        return self.full_title()

    def full_title(self):
        """
        Для текущего адреса получаем иерархию вверх, до страны.
        И возвращаем строковую интерпретацию этого полного адреса.
        """

        addr_id = int(self.pk)
        return AddressModelManager.get_address_full_title(
            addr_id=addr_id
        )

    def get_id_hierarchy_gen(self):
        ids_tree_query = AddressModelManager.get_address_recursive_ids(
            addr_id=self.pk,
            direction_down=False
        )
        for addr in AddressModel.objects.filter(pk__in=ids_tree_query):
            yield addr.pk

    def get_address_item_by_type(self, addr_type: AddressModelTypes) -> Optional[AddressModel]:
        """
        :param addr_type: Id нижнего адресного объекта.

        Для текущего адреса получаем иерархию вверх, до страны.
        Из этой иерархии берём только первый попавшийся элемент
        с AddressModel.address_type = addr_type
        """
        return AddressModel.objects.get_address_by_type(
            addr_id=safe_int(self.pk),
            addr_type=addr_type
        ).order_by('-address_type').first()

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

    def save(self, *args, **kwargs):
        """Нельзя чтобы у адресного объекта его тип был таким же как и у родителя.
           Например улица не может находится в улице, дом в доме, а город в городе.
        """
        qs = AddressModel.objects.annotate(
            # Считаем всех потомков, у которых тип адреса как а родителя
            children_addrs_count=Count('addressmodel', filter=Q(addressmodel__fias_address_type=self.fias_address_type))
        ).filter(
            Q(parent_addr__fias_address_type=self.fias_address_type) | # Сверяемся с родителем
            Q(children_addrs_count__gt=0),
            pk=self.pk
        )
        if qs.exists():
            raise ValidationError(
                'У родительского адресного объекта не может '
                'быть такой же тип как у родителя'
            )
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def __repr__(self):
        return "<%s> %s" % (self.get_address_type_display(), self.title)

    @property
    def parent_addr_title(self) -> Optional[str]:
        if self.parent_addr:
            return str(self.parent_addr.title)

    @property
    def fias_address_level_name(self):
        fn = getattr(self, 'get_fias_address_level_display', None)
        if fn is None:
            return
        return fn()

    @property
    def fias_address_type_name(self):
        fn = getattr(self, 'get_fias_address_type_display', None)
        if fn is None:
            return
        return fn()

    class Meta:
        db_table = 'addresses'
        unique_together = ('parent_addr', 'address_type', 'fias_address_type', 'title')

