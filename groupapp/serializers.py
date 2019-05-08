from rest_framework import serializers
from groupapp.models import Group


class GroupsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('pk', 'title', 'code')
