from django.urls import path, include
from rest_framework.routers import DefaultRouter
from messenger import views

app_name = 'messenger'

router = DefaultRouter()
router.register('viber/subscriber', views.ViberSubscriberModelViewSet)
router.register('viber/msg', views.ViberMessageModelViewSet)
router.register('viber', views.ViberMessengerModelViewSet)
router.register('', views.MessengerModelViewSet)

urlpatterns = [
    path('', include(router.urls))
]
