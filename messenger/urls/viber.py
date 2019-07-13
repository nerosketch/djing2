from django.urls import path, include
from rest_framework.routers import DefaultRouter
from messenger.views import viber


router = DefaultRouter()
router.register('subscriber', viber.ViberSubscriberModelViewSet)
router.register('msg', viber.ViberMessageModelViewSet)
router.register('', viber.ViberMessengerModelViewSet)


urlpatterns_viber = [
    path('<slug:boturl>/listen/', viber.ListenViberView.as_view(), name='listen_viber_bot'),
    path('', include(router.urls))
]
