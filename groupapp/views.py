from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from djing2.viewsets import DjingModelViewSet
from groupapp.models import Group
from groupapp.serializers import GroupsSerializer
from profiles.serializers import PermissionModelSerializer


class GroupsModelViewSets(DjingModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupsSerializer
    filter_backends = (OrderingFilter,)
    ordering_fields = 'title',

    @action(detail=False)
    def get_all_related_perms(self, request):
        related_perms_qs = Group.objects.get_perms4related_models()

        serializer = PermissionModelSerializer(related_perms_qs, many=True)
        return Response(serializer.data)
