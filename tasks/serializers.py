from rest_framework import serializers

from djing2.lib.mixins import BaseCustomModelSerializer
from tasks import models
from profiles.models import UserProfile


class ChangeLogModelSerializer(BaseCustomModelSerializer):
    who_name = serializers.CharField(source='who.get_full_name', read_only=True)
    act_text = serializers.CharField(source='get_act_type_display', read_only=True)
    task_descr = serializers.CharField(source='task.descr', read_only=True)

    class Meta:
        model = models.ChangeLog
        fields = '__all__'


class TaskModelSerializer(BaseCustomModelSerializer):
    author_full_name = serializers.CharField(source='author.get_full_name', read_only=True)
    author_uname = serializers.CharField(source='author.username', read_only=True)
    priority_name = serializers.CharField(source='get_priority_display', read_only=True)
    time_diff = serializers.CharField(source='get_time_diff', read_only=True)
    customer_address = serializers.CharField(source='customer.get_address', read_only=True)
    customer_full_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_uname = serializers.CharField(source='customer.username', read_only=True)
    customer_group = serializers.IntegerField(source='customer.group_id', read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    recipients = serializers.PrimaryKeyRelatedField(many=True, queryset=UserProfile.objects.only('pk', 'username', 'fio'))
    state_str = serializers.CharField(source='get_task_state_display', read_only=True)
    mode_str = serializers.CharField(source='get_mode_display', read_only=True)
    time_of_create = serializers.DateTimeField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = models.Task
        fields = '__all__'


class UserTaskModelSerializer(TaskModelSerializer):
    class Meta(TaskModelSerializer.Meta):
        fields = ('time_of_create', 'state_str', 'mode_str', 'out_date')


class ExtraCommentModelSerializer(BaseCustomModelSerializer):
    author_id = serializers.IntegerField(source='author.pk', read_only=True)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    author_avatar = serializers.CharField(source='author.get_avatar_url', read_only=True)
    can_remove = serializers.SerializerMethodField(method_name='_can_remove')

    def _can_remove(self, obj):
        return self.context['request'].user.pk == obj.author_id

    class Meta:
        model = models.ExtraComment
        exclude = ('author',)


class TaskDocumentAttachmentSerializer(BaseCustomModelSerializer):
    author = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = models.TaskDocumentAttachment
        fields = '__all__'
