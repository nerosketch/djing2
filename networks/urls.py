from django.urls import path, include
from rest_framework.routers import DefaultRouter
from networks.views import generic, radius

app_name = 'networks'

router = DefaultRouter()

# Radius api
router.register('radius', radius.CustomerRadiusAuthViewSet)

router.register('vlan', generic.VlanIfModelViewSet)
router.register('', generic.NetworkModelViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
