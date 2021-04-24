from django.contrib import admin
from networks import models

admin.site.register(models.NetworkIpPool)
admin.site.register(models.VlanIf)
