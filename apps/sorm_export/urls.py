from django.urls import path, include
from rest_framework.routers import DefaultRouter
from sorm_export.views import SormCustomersWithoutContractsListView


app_name = 'sorm_export'

router = DefaultRouter()
router.register('', SormCustomersWithoutContractsListView)

urlpatterns = [
    path('', include(router.urls))
]

