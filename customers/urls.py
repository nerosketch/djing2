from django.urls import path, include
from rest_framework.routers import DefaultRouter
from customers import views


app_name = 'customers'


router = DefaultRouter()
router.register('customer-service', views.CustomerServiceModelViewSet)
router.register('streets', views.CustomerStreetModelViewSet)
router.register('customer-log', views.CustomerLogModelViewSet)
router.register('passport', views.PassportInfoModelViewSet)
router.register('invoices', views.InvoiceForPaymentModelViewSet)
router.register('customer-raw-password', views.CustomerRawPasswordModelViewSet)
router.register('additional-telephone', views.AdditionalTelephoneModelViewSet)
router.register('periodic-pay', views.PeriodicPayForIdModelViewSet)
router.register('', views.CustomerModelViewSet)

urlpatterns = [
    path('generate_username/', views.CustomerModelViewSet.as_view({'get': 'generate_random_username'})),
    path('generate_password/', views.CustomerModelViewSet.as_view({'get': 'generate_random_password'})),
    path('attach_group_service/', views.AttachServicesToGroups.as_view()),
    path('', include(router.urls)),
]
