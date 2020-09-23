from typing import List

from django.contrib.auth.models import Permission, Group as ProfileGroup
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.shortcuts import resolve_url
from django.db import models
from guardian.shortcuts import assign_perm

from djing2.lib import safe_int
from djing2.lib.validators import latinValidator
from djing2.models import BaseAbstractModel


class GroupManager(models.Manager):

    def get_all_related_models(self):
        g = self.select_related()
        return tuple(rel_item.related_model for rel_name, rel_item in g.model._meta.fields_map.items())

    def get_perms4related_models(self):
        related_models = self.get_all_related_models()
        ctypes = ContentType.objects.get_for_models(*related_models)
        ctype_ids = [ct.pk for md, ct in ctypes.items()]
        related_perms = Permission.objects.filter(
            content_type__in=ctype_ids
        )
        return related_perms


class Group(BaseAbstractModel):
    title = models.CharField(_('Title'), max_length=127, unique=True)
    # Code is deprecated
    code = models.CharField(
        _('Tech code'), blank=True, null=True,
        default=None, max_length=12,
        validators=[latinValidator]
    )

    objects = GroupManager()

    def get_absolute_url(self):
        return resolve_url('group_app:edit', self.pk)

    def set_permissions_recursive(self, permission_ids: List[int], profile_group: ProfileGroup) -> bool:
        permission_ids = [safe_int(pk) for pk in permission_ids if safe_int(pk) > 0]
        if len(permission_ids) == 0:
            return False

        related_models = Group.objects.get_all_related_models()
        related_ctypes = ContentType.objects.get_for_models(*related_models)

        _tmp_all_perms = Permission.objects.filter(pk__in=permission_ids)

        # TODO: Optimize
        for rel_mod, rel_ctype in related_ctypes.items():
            perms = Permission.objects.filter(content_type=rel_ctype, pk__in=permission_ids)
            for perm in perms:
                if hasattr(rel_mod, 'group'):
                    related_objs = rel_mod.objects.filter(group=self)
                    assign_perm(perm, profile_group, related_objs)
        return True

    class Meta:
        db_table = 'groups'
        verbose_name = _('Group')
        verbose_name_plural = _('Groups')
        ordering = 'title',

    def __str__(self):
        return self.title


# @receiver(pre_save, sender=Group)
# def group_pre_save(sender, instance, **kwargs):
#     """
#     Tech code must be unique or empty
#     """
#     if not instance.code:
#         return
#     if Group.objects.filter(code=instance.code).exists():
#         raise ValidationError(_('Tech code must be unique'))
