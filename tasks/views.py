from django.db.models import Count
from django.utils.translation import gettext
from guardian.shortcuts import get_objects_for_user
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from djing2.lib import safe_int
from djing2.viewsets import DjingModelViewSet, DjingListAPIView, BaseNonAdminReadOnlyModelViewSet
from profiles.models import UserProfile
from tasks import models
from tasks import serializers


class ChangeLogModelViewSet(DjingModelViewSet):
    queryset = models.ChangeLog.objects.select_related(
        'who', 'task'
    ).only(
        'id', 'who', 'who__username', 'who__fio',
        'act_type', 'when', 'task', 'task__descr'
    )
    serializer_class = serializers.ChangeLogModelSerializer
    filterset_fields = ('act_type', 'who', 'task')


class TaskModelViewSet(DjingModelViewSet):
    queryset = models.Task.objects.select_related(
        'author', 'customer', 'customer__group', 'customer__street'
    ).annotate(comment_count=Count('extracomment'))
    serializer_class = serializers.TaskModelSerializer
    filterset_fields = ('task_state', 'recipients', 'customer')

    def destroy(self, request, *args, **kwargs):
        task = self.get_object()
        if request.user.is_superuser or request.user not in task.recipients.all():
            self.perform_destroy(task)
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response(
                gettext('You cannot delete task that assigned to you'),
                status=status.HTTP_403_FORBIDDEN
            )

    def create(self, request, *args, **kwargs):
        # check if new task with user already exists
        uname = request.query_params.get('uname')
        if uname:
            exists_task = models.Task.objects.filter(
                customer__username=uname,
                task_state=models.Task.TASK_STATE_NEW
            )
            if exists_task.exists():
                return Response(
                    gettext('New task with this customer already exists.'),
                    status=status.HTTP_409_CONFLICT
                )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer, *args, **kwargs):
        return super().perform_create(
            serializer=serializer,
            author=self.request.user,
            site=self.request.site
        )

    @action(detail=False, permission_classes=[IsAuthenticated, IsAdminUser])
    def active_task_count(self, request):
        tasks_count = 0
        if isinstance(request.user, UserProfile):
            tasks_count = models.Task.objects.filter(
                recipients__in=(request.user,),
                task_state=models.Task.TASK_STATE_NEW
            ).count()
        return Response(tasks_count)

    @action(detail=True)
    def finish(self, request, pk=None):
        task = self.get_object()
        task.finish(request.user)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True)
    def failed(self, request, pk=None):
        task = self.get_object()
        task.do_fail(request.user)
        return Response(status=status.HTTP_200_OK)

    @action(detail=True)
    def remind(self, request, pk=None):
        self.check_permission_code(request, 'tasks.can_remind')
        task = self.get_object()
        task.send_notification()
        return Response(status=status.HTTP_200_OK)

    @action(detail=False, url_path="new_task_initial/(?P<group_id>\d{1,18})/(?P<customer_id>\d{1,18})")
    def new_task_initial(self, request, group_id: str, customer_id: str):
        customer_id = safe_int(customer_id)
        if customer_id == 0:
            return Response('bad customer_id', status=status.HTTP_400_BAD_REQUEST)
        exists_task = models.Task.objects.filter(
            customer__id=customer_id,
            task_state=models.Task.TASK_STATE_NEW
        )
        if exists_task.exists():
            # Task with this customer already exists
            return Response({
                'status': 0,
                'text': gettext('New task with this customer already exists.'),
                'task_id': exists_task.first().pk
            })

        group_id = safe_int(group_id)
        if group_id > 0:
            recipients = UserProfile.objects.get_profiles_by_group(
                group_id=group_id
            ).only('pk').values_list(
                'pk', flat=True
            )
            return Response({
                'status': 1,
                'recipients': recipients
            })
        return Response('"group_id" parameter is required', status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False)
    def state_percent_report(self, request):
        def _build_format(num: int, name: str):
            state_count, state_percent = models.Task.objects.task_state_percent(
                task_state=int(num)
            )
            return {
                'num': num,
                'name': name,
                'count': state_count,
                'percent': state_percent
            }
        r = [_build_format(task_state_num, task_state_name) for task_state_num, task_state_name in models.Task.TASK_STATES]

        return Response(r)

    @action(detail=False)
    def task_mode_report(self, request):
        report = models.Task.objects.task_mode_report()

        def _get_display(val: int) -> str:
            r = (str(ttext) for tval, ttext in models.Task.TASK_TYPES if tval == val)
            try:
                return next(r)
            except StopIteration:
                return ''
        res = [{
            'mode': _get_display(vals.get('mode')),
            'task_count': vals.get('task_count')
        } for vals in report.values('mode', 'task_count')]
        return Response({
            'annotation': res
        })


class AllTasksList(DjingListAPIView):
    serializer_class = serializers.TaskModelSerializer

    def get_queryset(self):
        qs = get_objects_for_user(
            user=self.request.user,
            perms='tasks.view_task',
            klass=models.Task
        )
        return qs.select_related(
            'customer', 'customer__street',
            'customer__group', 'author'
        ).annotate(comment_count=Count('extracomment'))


class AllNewTasksList(AllTasksList):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(task_state=models.Task.TASK_STATE_NEW)


class NewTasksList(AllTasksList):
    """
    Returns tasks that new for current user
    """

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            recipients=self.request.user, task_state=models.Task.TASK_STATE_NEW
        )


class FailedTasksList(AllTasksList):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            recipients=self.request.user, task_state=models.Task.TASK_STATE_CONFUSED
        )


class FinishedTasksList(AllTasksList):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            recipients=self.request.user, task_state=models.Task.TASK_STATE_COMPLETED
        )


class OwnTasksList(AllTasksList):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            author=self.request.user
        ).exclude(task_state=models.Task.TASK_STATE_COMPLETED)


class MyTasksList(AllTasksList):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            recipients=self.request.user
        )


class ExtraCommentModelViewSet(DjingModelViewSet):
    queryset = models.ExtraComment.objects.all()
    serializer_class = serializers.ExtraCommentModelSerializer
    filterset_fields = ('task', 'author')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.author == self.request.user:
            self.perform_destroy(comment)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_403_FORBIDDEN)


class UserTaskHistory(BaseNonAdminReadOnlyModelViewSet):
    queryset = models.Task.objects.annotate(comment_count=Count('extracomment'))
    serializer_class = serializers.UserTaskModelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(customer__id=self.request.user.pk)


class TaskDocumentAttachmentViewSet(DjingModelViewSet):
    queryset = models.TaskDocumentAttachment.objects.all()
    serializer_class = serializers.TaskDocumentAttachmentSerializer
    filterset_fields = ('task',)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
