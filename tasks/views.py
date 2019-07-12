from django.contrib.auth import get_user_model
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
    queryset = models.Task.objects.all()
    serializer_class = serializers.TaskModelSerializer

    @action(detail=True)
    def active_task_count(self, request):
        tasks_count = 0
        if isinstance(request.user, UserProfile):
            tasks_count = models.Task.objects.filter(recipients__in=request.user, state=0).count()
        return Response(tasks_count)


class ExtraCommentModelViewSet(DjingModelViewSet):
    queryset = models.ExtraComment.objects.all()
    serializer_class = serializers.ExtraCommentModelSerializer
