from django.urls import path, include
from rest_framework.routers import DefaultRouter
from devices import views


app_name = 'devices'


router = DefaultRouter()
router.register('', views.DeviceModelViewSet)
router.register('ports/', views.PortModelViewSet)

urlpatterns = [
    path('groups/', views.DeviceGroupsList.as_view(), name='groups'),
    path('', include(router.urls)),
]
