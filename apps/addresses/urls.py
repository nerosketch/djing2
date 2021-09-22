from django.urls import path, include
from rest_framework.routers import DefaultRouter
from addresses import views


app_name = 'addresses'

router = DefaultRouter()
router.register('', views.AddressModelViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
