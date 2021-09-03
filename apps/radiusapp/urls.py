from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import customers
from .views import session_views

app_name = "radiusapp"

router = DefaultRouter()

# customer radius views
router.register("customer", customers.RadiusCustomerServiceRequestViewSet, basename="customer")

router.register("session", session_views.CustomerRadiusSessionModelViewSet)

urlpatterns = [path("", include(router.urls))]
