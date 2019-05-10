from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from groupapp.models import Group
from groupapp.serializers import GroupsSerializer


class GroupsModelViewSets(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupsSerializer
    permission_classes = (IsAuthenticated,)
