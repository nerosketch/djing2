from django.urls import include, path
from rest_framework.routers import DefaultRouter

from customers.views import admin_side, user_side

app_name = "customers"


router = DefaultRouter()

# User side views
router.register("users/service", user_side.CustomerServiceModelViewSet)
router.register("users/log", user_side.LogsReadOnlyModelViewSet)
router.register("users/debts", user_side.DebtsList)

# Admin Views
router.register("dynamic-fields", admin_side.CustomerDynamicFieldContentModelViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
