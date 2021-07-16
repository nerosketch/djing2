from django.urls import path, include
from messenger import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('subscriber', views.SubscriberModelViewSet)
router.register('', views.MessengerModelViewSet, basename='messenger')

app_name = "messenger"

urlpatterns = [
    path("", include(router.urls)),
]
