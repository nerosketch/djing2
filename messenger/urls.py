from django.urls import path, include
from rest_framework.routers import DefaultRouter

from messenger import views

app_name = 'messenger'

router = DefaultRouter()
router.register('subscriber', views.SubscriberModelViewSet)
router.register('msg', views.MessageModelViewSet)
router.register('', views.MessengerModelViewSet)

urlpatterns = [
    path('', include(router.urls))
]
