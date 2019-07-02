from django.urls import path, include
from rest_framework.routers import DefaultRouter
from customers import views


app_name = 'customers'


router = DefaultRouter()
router.register('', views.SubscriberModelViewSet)
router.register('subscriber-service', views.SubscriberServiceModelViewSet)
router.register('subscriber-street', views.SubscriberStreetModelViewSet)
router.register('subscriber-log', views.SubscriberLogModelViewSet)
router.register('passport', views.PassportInfoModelViewSet)
router.register('invoices', views.InvoiceForPaymentModelViewSet)
router.register('subscriber-raw-password', views.SubscriberRawPasswordModelViewSet)
router.register('additional-telephone', views.AdditionalTelephoneModelViewSet)
router.register('periodic-pay', views.PeriodicPayForIdModelViewSet)

urlpatterns = [
    path('generate_username/', views.SubscriberModelViewSet.as_view({'get': 'generate_random_username'})),
    path('generate_password/', views.SubscriberModelViewSet.as_view({'get': 'generate_random_password'})),
    path('', include(router.urls)),
]
