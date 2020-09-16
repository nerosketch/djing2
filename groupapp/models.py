# from django.db.models.signals import pre_save
# from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.shortcuts import resolve_url
from django.db import models
# from rest_framework.exceptions import ValidationError
from djing2.lib.validators import latinValidator


class Group(models.Model):
    title = models.CharField(_('Title'), max_length=127, unique=True)
    # Code is deprecated
    code = models.CharField(
        _('Tech code'), blank=True, null=True,
        default=None, max_length=12,
        validators=(latinValidator,)
    )

    def get_absolute_url(self):
        return resolve_url('group_app:edit', self.pk)

    @staticmethod
    def get_all_related_models():
        g = Group.objects.select_related()
        return tuple(rel_item.related_model for rel_name, rel_item in g.model._meta.fields_map.items())

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
