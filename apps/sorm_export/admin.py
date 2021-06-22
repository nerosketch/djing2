from django.contrib import admin

from sorm_export.models import ExportStampModel, FiasRecursiveAddressModel


admin.site.register(ExportStampModel)
admin.site.register(FiasRecursiveAddressModel)
