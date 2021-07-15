from django.contrib import admin
from fin_app.models import alltime

admin.site.register(alltime.PayAllTimeGateway)
admin.site.register(alltime.AllTimePayLog)
