from django.contrib import admin
from addresses.models import LocalityModel, StreetModel

admin.site.register(LocalityModel)
admin.site.register(StreetModel)
