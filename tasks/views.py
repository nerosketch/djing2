from django.contrib.auth import get_user_model
from django.utils.translation import gettext
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from djing2.viewsets import DjingModelViewSet, DjingListAPIView
from profiles.serializers import UserProfileSerializer
from tasks import models
from tasks import serializers


class ChangeLogModelViewSet(DjingModelViewSet):
    queryset = models.ChangeLog.objects.all()
    serializer_class = serializers.ChangeLogModelSerializer


UserProfile = get_user_model()


class TaskModelViewSet(DjingModelViewSet):
    queryset = models.Task.objects.all().select_related(
        'author', 'customer', 'customer__group', 'customer__street'
    ).only(
        'author__username', 'author__fio', 'priority', 'out_date',
        'customer__group__title', 'customer__street__name',
        'customer__username', 'customer__fio', 'customer__house',
        'state', 'mode', 'time_of_create', 'descr', 'recipients'
    )
    # TODO: Optimize. recipients field make request for each task entry
    serializer_class = serializers.TaskModelSerializer
    filterset_fields = ('state', 'recipients', 'customer')

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
            exists_task = models.Task.objects.filter(customer__username=uname, state=0)
            if exists_task.exists():
                return Response(
                    gettext('New task with this customer already exists.'),
                    status=status.HTTP_409_CONFLICT
                )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(
            author=self.request.user
        )

    @action(detail=False)
    def active_task_count(self, request):
        tasks_count = 0
        if isinstance(request.user, UserProfile):
            tasks_count = models.Task.objects.filter(recipients__in=(request.user,), state=0).count()
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
        task = self.get_object()
        task.send_notification()
        return Response(status=status.HTTP_200_OK)

    @action(detail=True)
    def recipients(self, request, pk=None):
        obj = self.get_object()
        recs = obj.recipients.all()
        ser = UserProfileSerializer(recs, many=True)
        return Response(ser.data)


class AllTasksList(DjingListAPIView):
    queryset = models.Task.objects.all().select_related(
        'customer', 'customer__street',
        'customer__group', 'author'
    )
    serializer_class = serializers.TaskModelSerializer


class AllNewTasksList(AllTasksList):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(state=0)


class NewTasksList(AllTasksList):
    """
    Returns tasks that new for current user
    """
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            recipients=self.request.user, state=0
        )


class FailedTasksList(AllTasksList):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            recipients=self.request.user, state=1
        )


class FinishedTasksList(AllTasksList):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            recipients=self.request.user, state=2
        )


class OwnTasksList(AllTasksList):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(
            author=self.request.user
        ).exclude(state=2)


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
