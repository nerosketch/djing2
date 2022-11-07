from django.contrib import admin
from customers import models

admin.site.register(models.Customer)
admin.site.register(models.CustomerLog)
admin.site.register(models.AdditionalTelephone)
admin.site.register(models.PassportInfo)
admin.site.register(models.InvoiceForPayment)
admin.site.register(models.CustomerRawPassword)
