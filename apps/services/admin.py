from django.contrib import admin
from services import models

admin.site.register(models.Service)
admin.site.register(models.PeriodicPay)
admin.site.register(models.OneShotPay)
