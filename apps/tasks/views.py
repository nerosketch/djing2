from django.db.models import Count
from django.utils.translation import gettext
from django.forms.models import model_to_dict
from django.http.response import Http404
from djing2.lib.fastapi.general_filter import general_filter_queryset
from djing2.lib.fastapi.pagination import paginate_qs_path_decorator
from djing2.lib.fastapi.types import IListResponse
from guardian.shortcuts import get_objects_for_user
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from fastapi import APIRouter, Depends, Request

from djing2.lib import safe_int
from djing2.viewsets import DjingModelViewSet, DjingListAPIView, BaseNonAdminReadOnlyModelViewSet
from djing2.lib.fastapi.auth import is_admin_auth_dependency, TOKEN_RESULT_TYPE, is_superuser_auth_dependency
from profiles.models import UserProfile
from tasks import models
from tasks import serializers


router = APIRouter(
    prefix='/tasks',
    tags=['Tasks'],
    dependencies=[Depends(is_admin_auth_dependency)]
)

class TasksQuerysetFilterMixin:
    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset=queryset)
        req = self.request
        if req.user.is_superuser:
            return qs
        return qs.filter(site=req.site)


@router.get('',
             response_model=IListResponse[CustomerResponseModelSchema],
             response_model_exclude_none=True
             )
@paginate_qs_path_decorator(schema=CustomerResponseModelSchema, db_model=models.Customer)
def get_all_tasks():
    customers_qs = general_filter_queryset(
        qs_or_model=models.Task,
        curr_site=curr_site,
        curr_user=curr_user,
        perm_codename='tasks.view_task'
    ).select_related(
        "author", "customer", "customer__group",
        "customer__address", "task_mode"
    ).annotate(
        comment_count=Count("extracomment"),
        doc_count=Count('taskdocumentattachment'),
    )



class TaskModelViewSet(TasksQuerysetFilterMixin, DjingModelViewSet):
    serializer_class = serializers.TaskModelSerializer
    filterset_fields = ("task_state", "recipients", "customer")

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        if request.user.is_superuser or request.user not in task.recipients.all():
            self.perform_destroy(task)
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                gettext("You cannot delete task that assigned to you"),
                status=status.HTTP_403_FORBIDDEN
            )

    def create(self, request, *args, **kwargs):
        # check if new task with user already exists
        uname = request.query_params.get("uname")
        if uname:
            exists_task = models.Task.objects.filter(
                customer__username=uname,
                task_state=models.TaskStates.TASK_STATE_NEW
            )
            if exists_task.exists():
                return Response(
                    gettext("New task with this customer already exists."),
                    status=status.HTTP_409_CONFLICT
                )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer, *args, **kwargs):
        return super().perform_create(
            serializer=serializer,
            author=self.request.user,
            site=self.request.site,
            *args, **kwargs
        )

    def perform_update(self, serializer, *args, **kwargs) -> None:
        new_data = dict(serializer.validated_data)
        old_data = model_to_dict(serializer.instance, exclude=["site", "customer"])
        instance = super().perform_update(serializer=serializer, *args, **kwargs)

        # Makes task change log.
        models.TaskStateChangeLogModel.objects.create_state_migration(
            task=instance, author=self.request.user, new_data=new_data, old_data=old_data
        )

    @action(detail=False, permission_classes=[IsAuthenticated, IsAdminUser])
    def active_task_count(self, request):
        tasks_count = 0
        if isinstance(request.user, UserProfile):
            tasks_count = models.Task.objects.filter(
                recipients__in=(request.user,),
                task_state=models.TaskStates.TASK_STATE_NEW
            ).count()
        return Response(tasks_count)

    @action(detail=True)
    def finish(self, request, pk=None):
        task = self.get_object()
        task.finish(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True)
    def failed(self, request, pk=None):
        task = self.get_object()
        task.do_fail(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True)
    def remind(self, request, pk=None):
        self.check_permission_code(request, "tasks.can_remind")
        task = self.get_object()
        task.send_notification()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, url_path=r"new_task_initial/(?P<group_id>\d{1,18})/(?P<customer_id>\d{1,18})")
    def new_task_initial(self, request, group_id: str, customer_id: str):
        customer_id_i = safe_int(customer_id)
        if customer_id_i == 0:
            return Response(
                "bad customer_id",
                status=status.HTTP_400_BAD_REQUEST
            )
        exists_task = models.Task.objects.filter(
            customer__id=customer_id_i,
            task_state=models.TaskStates.TASK_STATE_NEW
        )
        if exists_task.exists():
            # Task with this customer already exists
            return Response(
                {
                    "status": 0,
                    "text": gettext("New task with this customer already exists."),
                    "task_id": exists_task.first().pk,
                }
            )

        group_id_i = safe_int(group_id)
        if group_id_i > 0:
            recipients = (
                UserProfile.objects.get_profiles_by_group(
                    group_id=group_id_i
                ).only("pk").values_list("pk", flat=True)
            )
            return Response({"status": 1, "recipients": recipients})
        return Response(
            '"group_id" parameter is required',
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=False)
    def state_percent_report(self, request):
        def _build_format(num: int, name: str):
            state_count, state_percent = models.Task.objects.task_state_percent(task_state=int(num))
            return {"num": num, "name": name, "count": state_count, "percent": state_percent}

        r = [
            _build_format(task_state_num, str(task_state_name))
            for task_state_num, task_state_name in models.Task.TASK_STATES
        ]

        return Response(r)

    @action(detail=False)
    def task_mode_report(self, request):
        self.check_permission_code(request, "tasks.can_view_task_mode_report")

        report = models.Task.objects.task_mode_report()

        task_types = {t.pk: t.title for t in models.TaskModeModel.objects.all()}

        def _get_display(val: int) -> str:
            return str(task_types.get(val, 'Not Found'))

        res = [
            {"mode": _get_display(vals.get("mode")), "task_count": vals.get("task_count")}
            for vals in report.values("mode", "task_count")
        ]
        return Response({"annotation": res})


class AllTasksList(TasksQuerysetFilterMixin, DjingListAPIView):
    serializer_class = serializers.TaskModelSerializer

    def get_queryset(self):
        qs = get_objects_for_user(user=self.request.user, perms="tasks.view_task", klass=models.Task).order_by("-id")
        return qs.select_related(
            "customer", "customer__address", "customer__group", "author", "task_mode"
        ).annotate(
            comment_count=Count("extracomment"), doc_count=Count('taskdocumentattachment')
        )


class AllNewTasksList(AllTasksList):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(task_state=models.TaskStates.TASK_STATE_NEW)


class NewTasksList(AllTasksList):
    """
    Returns tasks that new for current user
    """

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            recipients=self.request.user,
            task_state=models.TaskStates.TASK_STATE_NEW
        )


class FailedTasksList(AllTasksList):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            recipients=self.request.user,
            task_state=models.TaskStates.TASK_STATE_CONFUSED
        )


class FinishedTasksList(AllTasksList):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            recipients=self.request.user,
            task_state=models.TaskStates.TASK_STATE_COMPLETED
        )


class OwnTasksList(AllTasksList):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            author=self.request.user
        ).exclude(
            task_state=models.TaskStates.TASK_STATE_COMPLETED
        )


class MyTasksList(AllTasksList):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(recipients=self.request.user)


class ExtraCommentModelViewSet(DjingModelViewSet):
    queryset = models.ExtraComment.objects.all()
    serializer_class = serializers.ExtraCommentModelSerializer
    filterset_fields = ("task", "author")

    def perform_create(self, serializer, *args, **kwargs):
        serializer.save(author=self.request.user)

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.author == self.request.user:
            self.perform_destroy(comment)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_403_FORBIDDEN)

    @action(detail=False)
    def combine_with_logs(self, request, *args, **kwargs):
        task_id = safe_int(request.query_params.get("task"))
        if task_id == 0:
            return Response('"task" param is required', status=status.HTTP_400_BAD_REQUEST)

        comments_list = self.get_serializer(
            self.get_queryset().filter(task_id=task_id).defer("task"),
            many=True
        ).data
        for comment in comments_list:
            comment.update({"type": "comment"})

        logs_list = serializers.TaskStateChangeLogModelSerializer(
            models.TaskStateChangeLogModel.objects.filter(task_id=task_id).defer("task"), many=True
        ).data
        for log in logs_list:
            log.update({"type": "log"})

        one_list = sorted(
            comments_list + logs_list,
            key=lambda i: i.get("when") or i.get("date_create"),
            reverse=True
        )

        return Response(one_list)


class UserTaskHistory(BaseNonAdminReadOnlyModelViewSet):
    queryset = models.Task.objects.annotate(comment_count=Count("extracomment"))
    serializer_class = serializers.UserTaskModelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(customer__id=self.request.user.pk)


class TaskDocumentAttachmentViewSet(DjingModelViewSet):
    queryset = models.TaskDocumentAttachment.objects.all()
    serializer_class = serializers.TaskDocumentAttachmentSerializer
    filterset_fields = ("task",)

    def perform_create(self, serializer, *args, **kwargs):
        serializer.save(author=self.request.user)


class TaskModeModelViewSet(DjingModelViewSet):
    queryset = models.TaskModeModel.objects.all()
    serializer_class = serializers.TaskModeModelSerializer


class TaskFinishDocumentModelViewSet(DjingModelViewSet):
    queryset = models.TaskFinishDocumentModel.objects.all()
    serializer_class = serializers.TaskFinishDocumentModelSerializer
    filterset_fields = ['task']

    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Http404:
            return Response(status=status.HTTP_204_NO_CONTENT)

    def create(self, request, *args, **kwargs):
        dat = {
            'author': request.user
        }
        dat.update(request.data)
        serializer = self.get_serializer(data=dat)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

