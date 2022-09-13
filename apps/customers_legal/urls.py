from django.urls import path, include
from rest_framework.routers import DefaultRouter
from customers_legal import views

app_name = 'customers_legal'


router = DefaultRouter()
router.register('dynamic', views.CustomerLegalDynamicFieldContentModelViewSet)
router.register('telephone', views.CustomerLegalTelephoneModelViewSet)

urlpatterns = [
    path('', include(router.urls))
]
