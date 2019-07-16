from rest_framework import serializers
from tasks import models


class ChangeLogModelSerializer(serializers.ModelSerializer):
    who_name = serializers.CharField(source='who.get_full_name', read_only=True)

    class Meta:
        model = models.ChangeLog
        fields = '__all__'


class TaskModelSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    customer_address = serializers.CharField(source='customer.get_address', read_only=True)
    comment_count = serializers.IntegerField(source='extracomment.count', read_only=True)
    recipients_count = serializers.IntegerField(source='recipients.count', read_only=True)
    state_str = serializers.CharField(source='get_state_display', read_only=True)
    mode_str = serializers.CharField(source='get_mode_display', read_only=True)
    time_of_create = serializers.DateTimeField(read_only=True)

    class Meta:
        model = models.Task
        exclude = ('author', 'recipients')
        depth = 1


class ExtraCommentModelSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = models.ExtraComment
        fields = '__all__'
