from django.contrib import admin
from devices import models

admin.site.register(models.Device)
admin.site.register(models.PortVlanMemberModel)
admin.site.register(models.Port)
