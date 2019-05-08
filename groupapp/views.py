from rest_framework import viewsets
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from groupapp.models import Group
from groupapp.serializers import GroupsSerializer


class GroupsModelViewSets(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupsSerializer


class GroupRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    # model = Group
    serializer_class = GroupsSerializer
    queryset = Group.objects.all()
