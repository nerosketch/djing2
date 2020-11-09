from django.urls import path, include
from rest_framework.routers import DefaultRouter
from profiles import views
from profiles.views import SitesObtainAuthToken

app_name = 'profiles'


router = DefaultRouter()
router.register('log', views.UserProfileLogViewSet)
router.register('current', views.CurrentAuthenticatedProfileROViewSet)
router.register('perms/object/user', views.UserObjectPermissionViewSet)
router.register('perms/object/group', views.GroupObjectPermissionViewSet)
router.register('perms/content-types', views.ContentTypeViewSet)
router.register('perms/groups', views.UserGroupModelViewSet)
router.register('perms', views.PermissionViewSet)
router.register('', views.UserProfileViewSet)


urlpatterns = [
    path('location-auth/', views.LocationAuth.as_view()),
    path('token-auth/', SitesObtainAuthToken.as_view()),
    path('', include(router.urls))
]
