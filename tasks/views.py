from django.contrib.auth import get_user_model
from django.utils.translation import gettext
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from djing2.viewsets import DjingModelViewSet
from tasks import models
from tasks import serializers


class ChangeLogModelViewSet(DjingModelViewSet):
    queryset = models.ChangeLog.objects.all()
    serializer_class = serializers.ChangeLogModelSerializer


UserProfile = get_user_model()


class TaskModelViewSet(DjingModelViewSet):
    queryset = models.Task.objects.all().select_related(
        'customer', 'customer__street', 'customer__group', 'author'
    )
    serializer_class = serializers.TaskModelSerializer
    filterset_fields = ('state', 'recipients')

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

    @action(detail=False)
    def active_task_count(self, request):
        tasks_count = 0
        if isinstance(request.user, UserProfile):
            tasks_count = models.Task.objects.filter(recipients__in=request.user, state=0).count()
        return Response(tasks_count)


class ExtraCommentModelViewSet(DjingModelViewSet):
    queryset = models.ExtraComment.objects.all()
    serializer_class = serializers.ExtraCommentModelSerializer
