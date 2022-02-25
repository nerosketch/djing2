from django.contrib.auth.models import Permission, Group as ProfileGroup
from rest_framework import serializers
from djing2.lib.mixins import BaseCustomModelSerializer

from groupapp.models import Group


class GroupsSerializer(BaseCustomModelSerializer):
    class Meta:
        model = Group
        fields = ("id", "title", "sites")


class SetRelatedPermsRecursiveSerializer(serializers.Serializer):

    permission_ids = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=Permission.objects.all()), required=True
    )
    profile_group = serializers.PrimaryKeyRelatedField(queryset=ProfileGroup.objects.all(), required=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass
