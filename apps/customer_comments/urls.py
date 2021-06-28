from django.urls import path, include
from rest_framework.routers import DefaultRouter
from customer_comments import views


app_name = 'customer_comments'


router = DefaultRouter()
router.register('', views.CustomerCommentModelViewSet)


urlpatterns = [
    path('', include(router.urls))
]
