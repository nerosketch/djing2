from django.urls import path, include, re_path
from rest_framework import routers
from groupapp import views


app_name = 'groups'


router = routers.DefaultRouter()
router.register('all', views.GroupsModelViewSets)


urlpatterns = [
    path('', include(router.urls)),
    path('<int:pk>/', views.GroupRetrieveUpdateDestroyAPIView.as_view())
]
