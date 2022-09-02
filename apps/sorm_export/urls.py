from django.urls import path, include
from rest_framework.routers import DefaultRouter
from sorm_export import views


app_name = 'sorm_export'

router = DefaultRouter()
router.register('contracts', views.SormCustomersWithoutContractsView, basename='contracts')
router.register('birth_day', views.SormCustomersTooOldView, basename='birth_day')

urlpatterns = [
    path('', include(router.urls))
]

