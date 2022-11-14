from typing import Optional

from django.contrib.sites.models import Site
from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.forms.models import model_to_dict
from django.utils.translation import gettext
from djing2.lib.fastapi.auth import is_admin_auth_dependency, TOKEN_RESULT_TYPE, is_customer_auth_dependency
from djing2.lib.fastapi.crud import CrudRouter
from djing2.lib.fastapi.general_filter import general_filter_queryset
from djing2.lib.fastapi.pagination import paginate_qs_path_decorator
from djing2.lib.fastapi.perms import filter_qs_by_rights, permission_check_dependency
from djing2.lib.fastapi.sites_depend import sites_dependency
from djing2.lib.fastapi.types import IListResponse, Pagination
from djing2.lib.fastapi.utils import AllOptionalMetaclass, create_get_initial_route, get_object_or_404
from djing2.lib.filters import filter_qs_by_fields_dependency
from fastapi import APIRouter, Depends, Request, Response, Path, Query, Form, UploadFile
from profiles.models import UserProfile
from starlette import status
from tasks import models
from tasks import schemas

router = APIRouter(
    prefix='/tasks',
    tags=['Tasks'],
    dependencies=[Depends(is_admin_auth_dependency)]
)

router.include_router(CrudRouter(
    schema=schemas.TaskDocumentAttachmentModelSchema,
    queryset=models.TaskDocumentAttachment.objects.all(),
    create_route=False,
    delete_one_route=False,
    update_route=False,
    get_all_route=False
), prefix='/attachment')


@router.delete('/attachment/{attachment_id}/',
               status_code=status.HTTP_204_NO_CONTENT,
               responses={
                   status.HTTP_204_NO_CONTENT: {
                       'description': 'Attachment successfully removed'
                   },
                   status.HTTP_403_FORBIDDEN: {
                       'description': "You can't delete this attachment"
                   }
               })
def delete_attachment(
    attachment_id: int,
    auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
):
    curr_user, token = auth
    attachments_qs = filter_qs_by_rights(
        qs_or_model=models.TaskDocumentAttachment,
        curr_user=curr_user,
        perm_codename='tasks.delete_taskdocumentattachment'
    ).filter(author=curr_user)
    attachment = get_object_or_404(attachments_qs, pk=attachment_id)
    attachment.delete()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post('/attachment/',
             response_model=schemas.TaskDocumentAttachmentModelSchema)
def create_customer_attachment(
    doc_file: UploadFile,
    title: str = Form(),
    task_id: int = Form(),
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='tasks.add_taskdocumentattachment'
    ))
):
    from django.core.files.base import ContentFile

    df = ContentFile(doc_file.file._file.read(), name=doc_file.filename)
    new_attachment = models.TaskDocumentAttachment.objects.create(
        title=title,
        doc_file=df,
        author=curr_user,
        task_id=task_id
    )
    return schemas.TaskDocumentAttachmentModelSchema.from_orm(new_attachment)


@router.get('/attachment/',
            response_model=IListResponse[schemas.TaskDocumentAttachmentModelSchema])
@paginate_qs_path_decorator(
    schema=schemas.TaskDocumentAttachmentModelSchema,
    db_model=models.TaskDocumentAttachment
)
def get_customer_attachments(
    request: Request,
    pagination: Pagination = Depends(),
    task_id: int = Query(gt=0),
):
    # TODO: authenticate
    qs = models.TaskDocumentAttachment.objects.filter(
        task_id=task_id
    )
    return qs


@router.get('/users/task_history/',
            response_model=IListResponse[schemas.UserTaskBaseSchema])
@paginate_qs_path_decorator(
    schema=schemas.UserTaskBaseSchema,
    db_model=models.Task
)
def get_user_task_history(
    request: Request,
    pagination: Pagination = Depends(),
    auth: TOKEN_RESULT_TYPE = Depends(is_customer_auth_dependency),
):
    curr_user, token = auth
    queryset = models.Task.objects.annotate(
        comment_count=Count("extracomment")
    ).filter(
        customer__id=curr_user.pk
    )
    return queryset


router.include_router(CrudRouter(
    schema=schemas.TaskFinishDocumentModelSchema,
    update_schema=schemas.TaskFinishDocumentBaseSchema,
    queryset=models.TaskFinishDocumentModel.objects.all(),
    create_route=False,
    get_all_route=False
), prefix='/finish_document')


@router.get('/finish_document/',
            response_model=IListResponse[schemas.TaskFinishDocumentModelSchema])
@paginate_qs_path_decorator(
    schema=schemas.TaskFinishDocumentModelSchema,
    db_model=models.TaskFinishDocumentModel
)
def get_finish_documents(
    request: Request,
    task_id: int = Query(gt=0),
    pagination: Pagination = Depends(),
):
    qs = models.TaskFinishDocumentModel.objects.filter(
        task_id=task_id
    )
    return qs


@router.post('/finish_document/',
             response_model=schemas.TaskFinishDocumentBaseSchema,
             status_code=status.HTTP_201_CREATED)
def create_finish_document(
    new_finish_doc: schemas.TaskFinishDocumentModelSchema,
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='tasks.add_taskfinishdocumentmodel'
    ))
):
    dat = new_finish_doc.dict(
        exclude_unset=True,
    )
    recs = dat.get('recipients', [])
    dat.update({
        'author': curr_user
    })
    with transaction.atomic():
        new_doc = models.TaskFinishDocumentModel.objects.create(**dat)
        new_doc.recipients.add(recs)

    return schemas.TaskFinishDocumentModelSchema.from_orm(new_doc)


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


router.include_router(CrudRouter(
    schema=schemas.TaskModeModelModelSchema,
    create_schema=schemas.TaskModeModelBaseSchema,
    queryset=models.TaskModeModel.objects.all(),
), prefix='/modes')


@router.get('/comments/combine_with_logs/',
            response_model=list)
def comments_combine_with_logs(
    task_id: int = Query(gt=0),
    auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
):
    curr_user, token = auth

    comment_qs = filter_qs_by_rights(
        qs_or_model=models.ExtraComment,
        curr_user=curr_user,
        perm_codename='tasks.view_extracomment'
    ).filter(task_id=task_id).defer("task")

    comments_list = [
        schemas.ExtraCommentModelSchema.from_orm(
            c,
        ).dict(exclude_unset=True)
        for c in comment_qs.iterator()
    ]
    for comment in comments_list:
        comment.update({"type": "comment"})

    logs_list = [
        schemas.TaskStateChangeLogModelSchema.from_orm(
            tscl
        ).dict(exclude_unset=True)
        for tscl in models.TaskStateChangeLogModel.objects.filter(
            task_id=task_id
        ).defer("task")
    ]
    for log in logs_list:
        log.update({"type": "log"})

    one_list = sorted(
        comments_list + logs_list,
        key=lambda i: i.get('when') or i.get('date_create'),
        reverse=True
    )

    return one_list


@router.delete('/comments/{comment_id}/',
               status_code=status.HTTP_204_NO_CONTENT,
               responses={
                   status.HTTP_204_NO_CONTENT: {
                       'description': 'Comment successfully removed'
                   },
                   status.HTTP_403_FORBIDDEN: {
                       'description': "You can't delete foreign comment"
                   }
               })
def delete_customer_comment(
    comment_id: int,
    auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
):
    curr_user, token = auth
    comment_qs = filter_qs_by_rights(
        qs_or_model=models.ExtraComment,
        curr_user=curr_user,
        perm_codename='tasks.delete_extracomment'
    )
    comment = get_object_or_404(comment_qs, pk=comment_id)

    if comment.author_id == curr_user.pk:
        comment.delete()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return Response(
        content=gettext("You can't delete foreign comment"),
        status_code=status.HTTP_403_FORBIDDEN
    )


@router.get(
    '/comments/',
    response_model=IListResponse[schemas.ExtraCommentModelSchema],
)
@paginate_qs_path_decorator(
    schema=TaskModelSchemaResponseModelSchema,
    db_model=models.Task
)
def get_all_comments(
    request: Request,
    pagination: Pagination = Depends(),
    task: Optional[int] = None, author: Optional[int] = None,
    auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
):
    curr_user, token = auth
    tasks_qs = filter_qs_by_rights(
        qs_or_model=models.ExtraComment,
        curr_user=curr_user,
        perm_codename='tasks.view_extracomment'
    )
    if task:
        tasks_qs = tasks_qs.filter(pk=task)
    if author:
        tasks_qs = tasks_qs.filter(author_id=author)

    return tasks_qs


@router.post(
    '/comments/',
    response_model=schemas.ExtraCommentModelSchema,
)
def create_customer_comment(
    comment_data: schemas.ExtraCommentBaseSchema,
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='tasks.add_extracomment'
    ))
):
    dat = comment_data.dict(exclude_unset=True)
    new_comment = models.ExtraComment.objects.create(**dat, author=curr_user)
    return schemas.ExtraCommentModelSchema.from_orm(new_comment)


create_get_initial_route(
    router=router,
    schema=schemas.TaskBaseSchema
)


@router.get('/active_task_count/',
            response_model=int)
def get_active_task_count(
    auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency)
):
    user, token = auth
    tasks_count = 0
    if isinstance(user, UserProfile):
        tasks_count = models.Task.objects.filter(
            recipients__in=(user,),
            task_state=models.TaskStates.TASK_STATE_NEW
        ).count()
    return tasks_count


@router.get(
    '/{task_id}/finish/',
    status_code=status.HTTP_204_NO_CONTENT
)
def finish_task(
    task_id: int,
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='tasks.can_finish_task'
    ))
):
    tasks_qs = filter_qs_by_rights(
        qs_or_model=models.Task,
        curr_user=curr_user,
        perm_codename='tasks.can_finish_task'
    )
    task = get_object_or_404(tasks_qs, pk=task_id)
    task.finish(curr_user)


@router.get(
    '/{task_id}/fail/',
    status_code=status.HTTP_204_NO_CONTENT
)
def fail_task(
    task_id: int,
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='tasks.can_fail_task'
    ))
):
    tasks_qs = filter_qs_by_rights(
        qs_or_model=models.Task,
        curr_user=curr_user,
        perm_codename='tasks.can_fail_task'
    )
    task = get_object_or_404(tasks_qs, pk=task_id)
    task.do_fail(curr_user)


@router.get('/{task_id}/remind/',
            status_code=status.HTTP_204_NO_CONTENT,
            response_model=None)
def remind_task(
    task_id: int,
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='tasks.tasks.can_remind'
    ))
):
    tasks_qs = filter_qs_by_rights(
        qs_or_model=models.Task,
        curr_user=curr_user,
        perm_codename='tasks.can_fail_task'
    )
    task = get_object_or_404(tasks_qs, pk=task_id)
    task.send_notification()


# TODO: add permission check
@router.get('/new_task_initial/{group_id}/{customer_id}/',
            response_model=dict)
def new_task_initial(group_id: int = Path(gt=0),
                     customer_id: int = Path(gt=0)):
    exists_task = models.Task.objects.filter(
        customer__id=customer_id,
        task_state=models.TaskStates.TASK_STATE_NEW
    )
    if exists_task.exists():
        # Task with this customer already exists
        return {
            "status": 0,
            "text": gettext("New task with this customer already exists."),
            "task_id": exists_task.first().pk,
        }
    recipients = list(
        UserProfile.objects.get_profiles_by_group(
            group_id=group_id
        ).only("pk").values_list("pk", flat=True)
    )
    return {
        "status": 1,
        "recipients": recipients
    }


@router.get(
    '/state_percent_report/',
    response_model=list[schemas.StatePercentResponseSchema],
    dependencies=[Depends(permission_check_dependency(
        perm_codename='tasks.can_view_reports'
    ))]
)
def state_percent_report():
    def _build_format(num: int, name: str):
        state_count, state_percent = models.Task.objects.task_state_percent(task_state=int(num))
        return schemas.StatePercentResponseSchema(
            num=num,
            name=name,
            count=state_count,
            percent=state_percent
        )

    r = (
        _build_format(task_state_num, str(task_state_name))
        for task_state_num, task_state_name in models.TaskStates.choices
    )
    return r


@router.get(
    '/task_mode_report/',
    response_model=schemas.TaskModeReportResponse,
    dependencies=[Depends(permission_check_dependency(
        perm_codename='tasks.can_view_task_mode_report'
    ))]
)
def task_mode_report():
    report = models.Task.objects.task_mode_report()
    task_types = {t.pk: t.title for t in models.TaskModeModel.objects.only('pk', 'title')}

    def _get_display(val: int) -> str:
        return str(task_types.get(val, 'Not Found'))

    res = (
        schemas.TaskModeReportAnnotationItem(
            mode=_get_display(vals.get("mode")),
            task_count=vals.get("task_count")
        )
        for vals in report.values("mode", "task_count")
    )
    return schemas.TaskModeReportResponse(
        annotation=res
    )


@router.get('/{task_id}/', response_model=schemas.TaskModelSchema)
def get_task_details(task_id: int,
                     auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency)
                     ):
    curr_user, token = auth
    tasks_qs = filter_qs_by_rights(
        qs_or_model=models.Task,
        curr_user=curr_user,
        perm_codename='tasks.view_task'
    )
    task = get_object_or_404(tasks_qs, pk=task_id)
    return schemas.TaskModelSchema.from_orm(task)


@router.patch('/{task_id}/',
              response_model=schemas.TaskModelSchema)
def update_task_info(task_id: int,
                     update_data: schemas.TaskUpdateSchema,
                     auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency)
                     ):
    curr_user, token = auth
    tasks_qs = filter_qs_by_rights(
        qs_or_model=models.Task,
        curr_user=curr_user,
        perm_codename='tasks.change_task'
    )
    task = get_object_or_404(tasks_qs, pk=task_id)
    pdata = update_data.dict(
        exclude_unset=True
    )
    recipients = pdata.pop('recipients', None)
    old_data = model_to_dict(task, exclude=["site", "customer"])
    for d_name, d_val in pdata.items():
        setattr(task, d_name, d_val)

    with transaction.atomic():
        task.save(update_fields=[d_name for d_name, d_val in pdata.items()])
        if recipients:
            task.recipients.set(recipients)

        # Makes task change log.
        models.TaskStateChangeLogModel.objects.create_state_migration(
            task=task,
            author=curr_user,
            new_data=pdata,
            old_data=old_data
        )
    return schemas.TaskModelSchema.from_orm(task)


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
    )
    # .annotate(
    #     recipients_agg=ArrayAgg('recipients')
    # )
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
