from django.db import models
from django.utils.translation import gettext_lazy as _
from devices.models import Device


class DotModel(models.Model):
    title = models.CharField(_('Map point title'), max_length=127)
    latitude = models.FloatField(_('Latitude'))
    longitude = models.FloatField(_('Longitude'))
    devices = models.ManyToManyField(Device, verbose_name=_('Devices'), db_table='dot_device')
    attachment = models.FileField(_('Attachment'), upload_to='map_attachments/%Y_%m_%d', null=True, blank=True)

    class Meta:
        db_table = 'maps_dots'
        verbose_name = _('Map point')
        verbose_name_plural = _('Map points')
        ordering = ('title',)

    def __str__(self):
        return self.title
