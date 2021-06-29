from django.urls import path, include
from rest_framework.routers import DefaultRouter
from tasks import views

app_name = "tasks"

router = DefaultRouter()
router.register("comments", views.ExtraCommentModelViewSet)
router.register("attachment", views.TaskDocumentAttachmentViewSet)
router.register("users/task_history", views.UserTaskHistory)
router.register("", views.TaskModelViewSet)


urlpatterns = [
    path("get_all/", views.AllTasksList.as_view()),
    path("get_all_new/", views.AllNewTasksList.as_view()),
    path("get_new/", views.NewTasksList.as_view()),
    path("get_failed/", views.FailedTasksList.as_view()),
    path("get_finished/", views.FinishedTasksList.as_view()),
    path("get_own/", views.OwnTasksList.as_view()),
    path("get_my/", views.MyTasksList.as_view()),
    path("", include(router.urls)),
]
