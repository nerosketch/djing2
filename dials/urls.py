from django.urls import path, include
from rest_framework.routers import DefaultRouter
from dials import views

app_name = 'dials'


router = DefaultRouter()
router.register('ats-devices', views.ATSDeviceModelViewSet)
router.register('dial-log', views.DialLogModelViewSet)
router.register('dial-accounts', views.DialAccountModelViewSet)


urlpatterns = [
    path('', include(router.urls)),
]
