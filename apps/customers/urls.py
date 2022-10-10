from django.urls import include, path
from rest_framework.routers import DefaultRouter

from customers.views import admin_side, user_side

app_name = "customers"


router = DefaultRouter()

# User side views
router.register("users/me", user_side.CustomersUserSideModelViewSet)
router.register("users/service", user_side.CustomerServiceModelViewSet)
router.register("users/log", user_side.LogsReadOnlyModelViewSet)
router.register("users/debts", user_side.DebtsList)

# Admin Views
router.register("customer-raw-password", admin_side.CustomerRawPasswordModelViewSet)
router.register("additional-telephone", admin_side.AdditionalTelephoneModelViewSet)
router.register("periodic-pay", admin_side.PeriodicPayForIdModelViewSet)
router.register("attachments", admin_side.CustomerAttachmentViewSet)
router.register("dynamic-fields", admin_side.CustomerDynamicFieldContentModelViewSet)
router.register("", admin_side.CustomerModelViewSet)

urlpatterns = [
    path("attach_group_service/", admin_side.AttachServicesToGroups.as_view()),
    path("groups_with_customers/", admin_side.groups_with_customers),
    path("customer-token", admin_side.SuperUserGetCustomerTokenByPhoneAPIView.as_view()),
    path("", include(router.urls)),
]
