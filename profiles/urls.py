from django.urls import path, include
from rest_framework.routers import DefaultRouter
from profiles import views


app_name = 'profiles'


router = DefaultRouter()
router.register('accounts', views.UserProfileViewSet)
router.register('log', views.UserProfileLogViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('token-auth/', views.CustomObtainAuthToken.as_view())
]
