from django.urls import path, include
from rest_framework import routers


app_name = "traf_stat"

router = routers.DefaultRouter()

urlpatterns = [path("", include(router.urls))]
