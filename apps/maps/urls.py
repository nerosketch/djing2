from django.urls import path, include
from rest_framework.routers import DefaultRouter
from maps import views


app_name = 'maps'


router = DefaultRouter()
router.register('', views.DotModelViewSet)

urlpatterns = [
    path('', include(router.urls))
]
