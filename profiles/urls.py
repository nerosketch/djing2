from django.urls import path, include
from rest_framework import routers
from profiles import views


app_name = 'profiles'


router = routers.DefaultRouter()
router.register('', views.UserProfileViewSet)
router.register('log', views.UserProfileLogViewSet)


urlpatterns = [
    path('', include(router.urls))
]
