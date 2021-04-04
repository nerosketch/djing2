from django.urls import path, include
from rest_framework.routers import DefaultRouter
from gateways.views import GatewayModelViewSet


app_name = "gateways"

router = DefaultRouter()
router.register("", GatewayModelViewSet)

urlpatterns = [path("", include(router.urls))]
