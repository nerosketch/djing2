from django.urls import path, include, re_path
from rest_framework import routers
from profiles import views


app_name = 'profiles'


router = routers.DefaultRouter()
router.register('all', views.UserProfileViewSet)
router.register('log', views.UserProfileLogViewSet)


urlpatterns = [
    path('', include(router.urls)),
    re_path(r'^(?P<username>\w{1,127})/$', views.UserProfileDetails.as_view())
]
