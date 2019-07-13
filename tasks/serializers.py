from rest_framework import serializers
from tasks import models


class ChangeLogModelSerializer(serializers.ModelSerializer):
    who_name = serializers.CharField(source='who.get_full_name', read_only=True)

    class Meta:
        model = models.ChangeLog
        fields = '__all__'


class TaskModelSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    comment_count = serializers.IntegerField(source='extracomment.count', read_only=True)

    class Meta:
        model = models.Task
        fields = '__all__'


class ExtraCommentModelSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = models.ExtraComment
        fields = '__all__'
