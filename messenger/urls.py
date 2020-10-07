from django.urls import path, include
from rest_framework.routers import DefaultRouter
from messenger.views import MessengerModelViewSet
from messenger.urls import viber
from messenger.urls import telegram


app_name = 'messenger'

router.register('', telegram.TelegramMessengerModelViewSet)
router.register('subscriber', viber.ViberSubscriberModelViewSet)
router.register('msg', viber.ViberMessageModelViewSet)
router.register('', viber.ViberMessengerModelViewSet)

router = DefaultRouter()
router.register('', MessengerModelViewSet)


urlpatterns = [
    path('viber/', include(viber.urlpatterns)),
    path('telegram/', include(telegram.urlpatterns)),
    path('', include(router.urls))
]
