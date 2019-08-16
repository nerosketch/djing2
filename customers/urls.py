from django.urls import path, include
from rest_framework.routers import DefaultRouter
from customers.views import admin_side, user_side


app_name = 'customers'


router = DefaultRouter()

# Admin Views
router.register('customer-service', admin_side.CustomerServiceModelViewSet)
router.register('streets', admin_side.CustomerStreetModelViewSet)
router.register('customer-log', admin_side.CustomerLogModelViewSet)
router.register('passport', admin_side.PassportInfoModelViewSet)
router.register('invoices', admin_side.InvoiceForPaymentModelViewSet)
router.register('customer-raw-password', admin_side.CustomerRawPasswordModelViewSet)
router.register('additional-telephone', admin_side.AdditionalTelephoneModelViewSet)
router.register('periodic-pay', admin_side.PeriodicPayForIdModelViewSet)
router.register('', admin_side.CustomerModelViewSet)

# User side views
router.register('users/customer', user_side.CustomersUserSideModelViewSet)
router.register('users/log', user_side.LogsReadOnlyModelViewSet)
router.register('users/debts', user_side.DebtsList)
router.register('users/task_history', user_side.TaskHistory)


urlpatterns = [
    path('generate_username/', admin_side.CustomerModelViewSet.as_view(actions={
        'get': 'generate_random_username'
    })),
    path('generate_password/', admin_side.CustomerModelViewSet.as_view(actions={
        'get': 'generate_random_password'
    })),
    path('attach_group_service/', admin_side.AttachServicesToGroups.as_view()),
    path('groups/', admin_side.CustomersGroupsListAPIView.as_view()),
    path('', include(router.urls)),
]
