from django.urls import path, include
from rest_framework.routers import SimpleRouter
from devices import views


app_name = 'devices'


router = SimpleRouter()
router.register('ports', views.PortModelViewSet)
router.register('', views.DeviceModelViewSet)

urlpatterns = [
    path('groups', views.DeviceGroupsList.as_view()),
    path('without_groups', views.DeviceWithoutGroupListAPIView.as_view()),
    path('', include(router.urls)),
]
