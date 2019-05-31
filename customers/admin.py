from django.contrib import admin
from customers import models

admin.site.register(models.Subscriber)
admin.site.register(models.SubscriberStreet)
