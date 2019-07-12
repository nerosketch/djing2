from django.urls import path, include
from rest_framework.routers import DefaultRouter
from tasks import views

app_name = 'tasks'

router = DefaultRouter()
router.register('comments', views.ExtraCommentModelViewSet)
router.register('log', views.ChangeLogModelViewSet)
router.register('', views.TaskModelViewSet)


urlpatterns = [
    path('', include(router.urls))
]
