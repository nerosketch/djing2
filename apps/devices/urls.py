from django.urls import path, include
from rest_framework.routers import DefaultRouter
from devices import views


app_name = "devices"


router = DefaultRouter()
router.register("ports-vlan", views.PortVlanMemberModelViewSet)
router.register("ports", views.PortModelViewSet)
router.register("pon", views.DevicePONViewSet)
router.register("all", views.DeviceModelViewSet)

urlpatterns = [
    path("localities/", views.DeviceLocalitiesList.as_view()),
    path("without_groups/", views.DeviceWithoutGroupListAPIView.as_view()),
    path("", include(router.urls)),
]
