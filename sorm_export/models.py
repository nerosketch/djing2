from django.utils.translation import gettext as _
from django.db import models


class ExportStampModel(models.Model):
    when = models.DateTimeField(_('Action time'), auto_now_add=True)

    class Meta:
        db_table = 'sorm_export_stamp'
