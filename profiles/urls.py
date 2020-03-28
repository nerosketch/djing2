from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter
from profiles import views


app_name = 'profiles'


router = DefaultRouter()
router.register('accounts', views.UserProfileViewSet)
router.register('log', views.UserProfileLogViewSet)
router.register('current', views.CurrentAuthenticatedProfileROViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('location-auth/', views.LocationAuth.as_view()),
    path('token-auth/', obtain_auth_token)
]
