from django.contrib import admin
from dials import models

admin.site.register(models.ATSDeviceModel)
admin.site.register(models.DialAccount)
admin.site.register(models.DialLog)
admin.site.register(models.SMSModel)