from django.urls import path, include
from rest_framework import routers
from groupapp import views


app_name = 'groups'


router = routers.DefaultRouter()
router.register('', views.GroupsModelViewSets)


urlpatterns = [
    path('', include(router.urls))
]
