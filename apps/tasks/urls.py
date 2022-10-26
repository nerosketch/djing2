from django.urls import path, include
from rest_framework.routers import DefaultRouter
from tasks import views

app_name = "tasks"

router = DefaultRouter()
router.register("comments", views.ExtraCommentModelViewSet)
router.register("attachment", views.TaskDocumentAttachmentViewSet)
router.register("users/task_history", views.UserTaskHistory)
router.register("modes", views.TaskModeModelViewSet)
router.register("finish_document", views.TaskFinishDocumentModelViewSet)
router.register("", views.TaskModelViewSet)


urlpatterns = [
    path("", include(router.urls)),
]
