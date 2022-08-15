from django.contrib import admin
from fin_app.models import alltime

admin.site.register(alltime.AllTimePayGateway)
admin.site.register(alltime.AllTimePaymentLog)
