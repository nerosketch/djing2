from rest_framework.routers import DefaultRouter
from messenger.views import viber


router = DefaultRouter()
router.register("subscriber", viber.ViberSubscriberModelViewSet)
router.register("msg", viber.ViberMessageModelViewSet)
router.register("", viber.ViberMessengerModelViewSet)


urlpatterns_viber = router.urls
