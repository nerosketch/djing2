from django.urls import path, include
from rest_framework import routers
from traf_stat import views

app_name = 'traf_stat'

router = routers.DefaultRouter()
router.register('cache', views.TrafficCacheViewSet)
router.register('archive', views.TrafficArchiveViewSet)

urlpatterns = [
    path('', include(router.urls))
]
