from django.urls import path, include
from rest_framework.routers import DefaultRouter
from messenger.views import MessengerModelViewSet
from messenger.urls.viber import urlpatterns_viber


app_name = "messenger"

router = DefaultRouter()
router.register("", MessengerModelViewSet)


urlpatterns = [path("viber/", include(urlpatterns_viber)), path("", include(router.urls))]
