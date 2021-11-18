from django.contrib import admin
from customers_legal import models


admin.site.register(models.CustomerLegalModel)
admin.site.register(models.CustomerLegalDynamicFieldContentModel)
