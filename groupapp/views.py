from rest_framework.filters import OrderingFilter
from rest_framework_guardian.filters import ObjectPermissionsFilter
from djing2.viewsets import DjingModelViewSet
from groupapp.models import Group
from groupapp.serializers import GroupsSerializer


class GroupsModelViewSets(DjingModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupsSerializer
    filter_backends = (OrderingFilter, ObjectPermissionsFilter)
    ordering_fields = ('title',)
