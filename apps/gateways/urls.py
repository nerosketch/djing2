from django.urls import path, include
from rest_framework.routers import DefaultRouter
from gateways.views import GatewayModelViewSet, gateway_class_choices


app_name = "gateways"

router = DefaultRouter()
# router.register("", GatewayModelViewSet)

urlpatterns = [
    path("gateway_class_choices/", gateway_class_choices),
    path("", include(router.urls))
]
