from django.urls import path, include
from rest_framework.routers import DefaultRouter
from networks import views

app_name = 'networks'

router = DefaultRouter()

router.register('', views.NetworkModelViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
