from typing import Optional

from django.contrib.postgres.aggregates.general import ArrayAgg
from django.contrib.sites.models import Site
from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.forms.models import model_to_dict
from django.http.response import Http404
from django.utils.translation import gettext
from djing2.lib import safe_int
from djing2.lib.fastapi.auth import is_admin_auth_dependency, TOKEN_RESULT_TYPE
from djing2.lib.fastapi.general_filter import general_filter_queryset
from djing2.lib.fastapi.pagination import paginate_qs_path_decorator
from djing2.lib.fastapi.perms import filter_qs_by_rights, permission_check_dependency
from djing2.lib.fastapi.sites_depend import sites_dependency
from djing2.lib.fastapi.types import IListResponse, Pagination
from djing2.lib.fastapi.utils import AllOptionalMetaclass, create_get_initial_route, get_object_or_404
from djing2.lib.filters import filter_qs_by_fields_dependency
from djing2.viewsets import DjingModelViewSet, BaseNonAdminReadOnlyModelViewSet
from fastapi import APIRouter, Depends, Request, Response
from profiles.models import UserProfile
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response as ResponseOld
from tasks import models
from tasks import schemas
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


class TaskModelSchemaResponseModelSchema(
    schemas.TaskModelSchema,
    metaclass=AllOptionalMetaclass
):
    pass


def get_all_tasks_dependency(
    auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
    curr_site: Site = Depends(sites_dependency),
    filter_fields_q: Q = Depends(filter_qs_by_fields_dependency(
        fields={
            'task_state': int, 'recipients': list[int], 'customer_id': int
        },
        db_model=models.Task
    )),
):
    curr_user, token = auth

    tasks_qs = filter_qs_by_rights(
        qs_or_model=models.Task,
        curr_user=curr_user,
        perm_codename='tasks.view_task'
    ).select_related(
        "author", "customer", "customer__group",
        "customer__address", "task_mode"
    ).annotate(
        comment_count=Count("extracomment"),
        doc_count=Count('taskdocumentattachment'),
        # recipients_agg=ArrayAgg('recipients')
    ).filter(filter_fields_q)

    if not curr_user.is_superuser:
        tasks_qs = tasks_qs.filter(site=curr_site)

    return tasks_qs.order_by('-id')


@router.delete('/{task_id}/',
               responses={
                   status.HTTP_204_NO_CONTENT: {
                       'description': 'Successfully removed'
                   },
                   status.HTTP_403_FORBIDDEN: {
                       'description': "Forbidden to remove task. May be you does not "
                                      "have rights, or you can't remove task assigned to you"
                   }
               },
               response_model=Optional[str])
def remove_task(task_id: int,
                curr_site: Site = Depends(sites_dependency),
                curr_user: UserProfile = Depends(permission_check_dependency(
                    perm_codename='tasks.delete_task'
                ))
                ):
    queryset = general_filter_queryset(
        qs_or_model=models.Task,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.delete_customer'
    ).annotate(
        recipients_agg=ArrayAgg('recipients')
    )
    task = get_object_or_404(queryset=queryset, pk=task_id)
    if curr_user.is_superuser or curr_user not in task.recipients_agg:
        task.delete()
    else:
        return Response(
            gettext("You cannot delete task assigned to you"),
            status_code=status.HTTP_403_FORBIDDEN
        )


@router.post('/',
             response_model=schemas.TaskModelSchema,
             status_code=status.HTTP_201_CREATED,
             responses={
                 status.HTTP_409_CONFLICT: {
                     'description': 'New task with this customer already exists.'
                 },
                 status.HTTP_201_CREATED: {
                     'description': 'New task successfully created'
                 }
             })
def create_new_task(new_task_data: schemas.TaskBaseSchema,
                    uname: Optional[str] = None,
                    curr_site: Site = Depends(sites_dependency),
                    curr_user: UserProfile = Depends(permission_check_dependency(
                        perm_codename='tasks.add_task'
                    ))
                    ):
    # check if new task with user already exists
    if uname:
        exists_task = models.Task.objects.filter(
            customer__username=uname,
            task_state=models.TaskStates.TASK_STATE_NEW
        )
        if exists_task.exists():
            return Response(
                gettext("New task with this customer already exists."),
                status_code=status.HTTP_409_CONFLICT
            )
    pdata = new_task_data.dict(exclude_unset=True, exclude={'recipients'})
    pdata.update({
        "author_id": curr_user.pk,
        "site_id": curr_site.pk
    })
    with transaction.atomic():
        new_task = models.Task.objects.create(**pdata)
        new_task.recipients.set(new_task_data.recipients)
    return schemas.TaskModelSchema.from_orm(new_task)


class TaskModelViewSet(TasksQuerysetFilterMixin, DjingModelViewSet):
    queryset = models.Task.objects.select_related(
        "author", "customer", "customer__group",
        "customer__address", "task_mode"
    ).annotate(
        comment_count=Count("extracomment"),
        doc_count=Count('taskdocumentattachment'),
    )
    serializer_class = serializers.TaskModelSerializer
    filterset_fields = ("task_state", "recipients", "customer")

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        if request.user.is_superuser or request.user not in task.recipients.all():
            self.perform_destroy(task)
            return ResponseOld(status=status.HTTP_204_NO_CONTENT)
        else:
            return ResponseOld(
                gettext("You cannot delete task assigned to you"),
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
                return ResponseOld(
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
        return ResponseOld(tasks_count)

    @action(detail=True)
    def finish(self, request, pk=None):
        task = self.get_object()
        task.finish(request.user)
        return ResponseOld(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True)
    def failed(self, request, pk=None):
        task = self.get_object()
        task.do_fail(request.user)
        return ResponseOld(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True)
    def remind(self, request, pk=None):
        self.check_permission_code(request, "tasks.can_remind")
        task = self.get_object()
        task.send_notification()
        return ResponseOld(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, url_path=r"new_task_initial/(?P<group_id>\d{1,18})/(?P<customer_id>\d{1,18})")
    def new_task_initial(self, request, group_id: str, customer_id: str):
        customer_id_i = safe_int(customer_id)
        if customer_id_i == 0:
            return ResponseOld(
                "bad customer_id",
                status=status.HTTP_400_BAD_REQUEST
            )
        exists_task = models.Task.objects.filter(
            customer__id=customer_id_i,
            task_state=models.TaskStates.TASK_STATE_NEW
        )
        if exists_task.exists():
            # Task with this customer already exists
            return ResponseOld(
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
            return ResponseOld({"status": 1, "recipients": recipients})
        return ResponseOld(
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
            for task_state_num, task_state_name in models.TaskStates.choices
        ]

        return ResponseOld(r)

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
        return ResponseOld({"annotation": res})


@router.get('/get_all/',
            response_model=IListResponse[TaskModelSchemaResponseModelSchema],
            response_model_exclude_none=True
            )
@paginate_qs_path_decorator(
    schema=TaskModelSchemaResponseModelSchema,
    db_model=models.Task
)
def get_all_tasks(request: Request,
                  pagination: Pagination = Depends(),
                  tasks_qs: QuerySet[models.Task] = Depends(get_all_tasks_dependency)
                  ):
    return tasks_qs


@router.get('/get_all_new/',
            response_model=IListResponse[TaskModelSchemaResponseModelSchema],
            response_model_exclude_none=True)
@paginate_qs_path_decorator(
    schema=TaskModelSchemaResponseModelSchema,
    db_model=models.Task
)
def get_all_new_task_list(request: Request,
                          pagination: Pagination = Depends(),
                          tasks_qs: QuerySet[models.Task] = Depends(get_all_tasks_dependency)
                          ):
    return tasks_qs.filter(task_state=models.TaskStates.TASK_STATE_NEW)


@router.get('/get_new/',
            response_model=IListResponse[TaskModelSchemaResponseModelSchema],
            response_model_exclude_none=True)
@paginate_qs_path_decorator(
    schema=TaskModelSchemaResponseModelSchema,
    db_model=models.Task
)
def get_new_task_list(request: Request,
                      pagination: Pagination = Depends(),
                      auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
                      tasks_qs: QuerySet[models.Task] = Depends(get_all_tasks_dependency)
                      ):
    """
    Returns tasks that new for current user
    """
    curr_user, token = auth

    return tasks_qs.filter(
        recipients=curr_user,
        task_state=models.TaskStates.TASK_STATE_NEW
    )


@router.get('/get_failed/',
            response_model=IListResponse[TaskModelSchemaResponseModelSchema],
            response_model_exclude_none=True)
@paginate_qs_path_decorator(
    schema=TaskModelSchemaResponseModelSchema,
    db_model=models.Task
)
def get_failed_task_list(request: Request,
                         pagination: Pagination = Depends(),
                         auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
                         tasks_qs: QuerySet[models.Task] = Depends(get_all_tasks_dependency)
                         ):
    """
    Returns tasks that new for current user
    """
    curr_user, token = auth

    return tasks_qs.filter(
        recipients=curr_user,
        task_state=models.TaskStates.TASK_STATE_CONFUSED
    )


@router.get('/get_finished/',
            response_model=IListResponse[TaskModelSchemaResponseModelSchema],
            response_model_exclude_none=True)
@paginate_qs_path_decorator(
    schema=TaskModelSchemaResponseModelSchema,
    db_model=models.Task
)
def get_finished_task_list(request: Request,
                           pagination: Pagination = Depends(),
                           auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
                           tasks_qs: QuerySet[models.Task] = Depends(get_all_tasks_dependency)
                           ):
    """
    Returns completed tasks for current user
    """
    curr_user, token = auth

    return tasks_qs.filter(
        recipients=curr_user,
        task_state=models.TaskStates.TASK_STATE_COMPLETED
    )


@router.get('/get_own/',
            response_model=IListResponse[TaskModelSchemaResponseModelSchema],
            response_model_exclude_none=True)
@paginate_qs_path_decorator(
    schema=TaskModelSchemaResponseModelSchema,
    db_model=models.Task
)
def get_my_own_task_list(request: Request,
                         pagination: Pagination = Depends(),
                         auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
                         tasks_qs: QuerySet[models.Task] = Depends(get_all_tasks_dependency)
                         ):
    """
    Returns own tasks for current user
    """
    curr_user, token = auth

    return tasks_qs.filter(
        author=curr_user,
    ).exclude(
        task_state=models.TaskStates.TASK_STATE_COMPLETED
    )


@router.get('/get_my/',
            response_model=IListResponse[TaskModelSchemaResponseModelSchema],
            response_model_exclude_none=True)
@paginate_qs_path_decorator(
    schema=TaskModelSchemaResponseModelSchema,
    db_model=models.Task
)
def get_my_task_list(request: Request,
                     pagination: Pagination = Depends(),
                     auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
                     tasks_qs: QuerySet[models.Task] = Depends(get_all_tasks_dependency)
                     ):
    curr_user, token = auth

    return tasks_qs.filter(
        recipients=curr_user,
    )


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
            return ResponseOld(status=status.HTTP_204_NO_CONTENT)
        return ResponseOld(status=status.HTTP_403_FORBIDDEN)

    @action(detail=False)
    def combine_with_logs(self, request, *args, **kwargs):
        task_id = safe_int(request.query_params.get("task"))
        if task_id == 0:
            return ResponseOld('"task" param is required', status=status.HTTP_400_BAD_REQUEST)

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

        return ResponseOld(one_list)


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
            return ResponseOld(status=status.HTTP_204_NO_CONTENT)

    def create(self, request, *args, **kwargs):
        dat = {
            'author': request.user
        }
        dat.update(request.data)
        serializer = self.get_serializer(data=dat)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return ResponseOld(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )


create_get_initial_route(
    router=router,
    schema=schemas.TaskBaseSchema
)
