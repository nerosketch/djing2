from django.contrib import admin
from messenger.models.messenger import Messenger
from messenger.models import viber

admin.site.register(Messenger)
admin.site.register(viber.ViberMessenger)
admin.site.register(viber.ViberMessage)
admin.site.register(viber.ViberSubscriber)
