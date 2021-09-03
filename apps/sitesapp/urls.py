from django.urls import path, include
from rest_framework.routers import DefaultRouter

from sitesapp.views import SiteModelViewSet

app_name = "sitesapp"

router = DefaultRouter()
router.register("", SiteModelViewSet)


urlpatterns = [path("", include(router.urls))]
