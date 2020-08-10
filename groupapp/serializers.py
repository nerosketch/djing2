from rest_framework.serializers import ModelSerializer
from drf_queryfields import QueryFieldsMixin

from groupapp.models import Group


class GroupsSerializer(QueryFieldsMixin, ModelSerializer):
    class Meta:
        model = Group
        fields = ('pk', 'title')
