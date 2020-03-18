from django.urls import path, include
from rest_framework.routers import DefaultRouter
from networks.views import generic, radius

app_name = 'networks'

router = DefaultRouter()

# Radius api
router.register('radius', radius.RadiusDHCPRequestViewSet, basename='radius')

router.register('lease', generic.CustomerIpLeaseModelViewSet)
router.register('pool', generic.NetworkIpPoolModelViewSet)
router.register('vlan', generic.VlanIfModelViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
