from django.contrib import admin
from messenger import models

admin.site.register(models.Messenger)
admin.site.register(models.MessengerMessage)
admin.site.register(models.MessengerSubscriber)
