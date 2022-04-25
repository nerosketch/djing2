from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import customers

app_name = "radiusapp"

router = DefaultRouter()

# customer radius views
router.register("customer", customers.RadiusCustomerServiceRequestViewSet, basename="customer")

urlpatterns = [path("", include(router.urls))]
