from django.urls import path, include
from rest_framework.routers import DefaultRouter
from webhooks.views import (
    HookObserverModelViewSet,
    ContentTypeModelViewSet
)

app_name = 'webhooks'

router = DefaultRouter()
router.register('content-type', ContentTypeModelViewSet)
router.register('', HookObserverModelViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
