from django.urls import path, include
from rest_framework.routers import DefaultRouter
from radiusapp.views import RadiusCustomerServiceRequestViewSet

app_name = "radiusapp"

router = DefaultRouter()

# customer radius views
router.register("customer", RadiusCustomerServiceRequestViewSet, basename="customer")

urlpatterns = [path("", include(router.urls))]
