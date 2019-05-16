from django.urls import path, include
from rest_framework.routers import DefaultRouter
from services import views

app_name = 'services'


router = DefaultRouter()
router.register('', views.ServiceModelViewSet)

urlpatterns = [
    path('', include(router.urls))
]
