from django.urls import path, include
from rest_framework.routers import DefaultRouter
from dynamicfields import views


router = DefaultRouter()
router.register('', views.FieldModelViewSet)

app_name = 'dynamicfields'

urlpatterns = [
    path('', include(router.urls))
]
