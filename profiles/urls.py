from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from profiles import views


app_name = 'profiles'


router = DefaultRouter()
router.register('', views.UserProfileViewSet)
router.register('log', views.UserProfileLogViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('api-token-auth/', obtain_auth_token)
]
