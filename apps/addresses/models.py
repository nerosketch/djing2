from django.db import models
from django.contrib.sites.models import Site
from django.utils.translation import gettext_lazy as _
from djing2.models import BaseAbstractModel


class LocalityModel(BaseAbstractModel):
    title = models.CharField(_('Title'), max_length=127, unique=True)
    sites = models.ManyToManyField(Site, blank=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'locality'


class StreetModel(BaseAbstractModel):
    name = models.CharField(_('Name'), max_length=64)
    locality = models.ForeignKey(LocalityModel, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "locality_street"
        verbose_name = _("Street")
        verbose_name_plural = _("Streets")
        ordering = ("name",)
        unique_together = ('name', 'locality')
