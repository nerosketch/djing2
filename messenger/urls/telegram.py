from rest_framework.routers import DefaultRouter
from messenger.views import telegram


router = DefaultRouter()
router.register('', telegram.TelegramMessengerModelViewSet)


urlpatterns = router.urls
