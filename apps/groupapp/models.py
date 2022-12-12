from django.contrib.sites.models import Site
from django.utils.translation import gettext_lazy as _
from django.shortcuts import resolve_url
from django.db import models

from djing2.models import BaseAbstractModel


class Group(BaseAbstractModel):
    title = models.CharField(_("Title"), max_length=127, unique=True)
    sites = models.ManyToManyField(Site, blank=True)

    def get_absolute_url(self):
        return resolve_url("group_app:edit", self.pk)

    class Meta:
        db_table = "groups"
        verbose_name = _("Group")
        verbose_name_plural = _("Groups")

    def __str__(self):
        return self.title
