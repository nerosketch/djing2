from django.urls import path, include
from rest_framework.routers import DefaultRouter
from networks import views

app_name = "networks"

router = DefaultRouter()

router.register("lease", views.CustomerIpLeaseModelViewSet)
router.register("pool", views.NetworkIpPoolModelViewSet)
router.register("vlan", views.VlanIfModelViewSet)


urlpatterns = [
    path("", include(router.urls)),
    path("find_customer_by_device_credentials/", views.FindCustomerByCredentials.as_view()),
    path("dhcp_lever/", views.DhcpLever.as_view()),
]
