from django.contrib import admin
from networks import models

admin.site.register(models.NetworkModel)
admin.site.register(models.VlanIf)