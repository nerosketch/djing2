from rest_framework.serializers import ModelSerializer

from groupapp.models import Group


class GroupsSerializer(ModelSerializer):
    class Meta:
        model = Group
        fields = ('pk', 'title', 'code')
