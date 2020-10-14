# from django.contrib.auth.models import Group as ProfileGroup
# from rest_framework import status
# from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
# from rest_framework.generics import get_object_or_404
# from rest_framework.response import Response

from djing2.lib.filters import CustomObjectPermissionsFilter
from djing2.viewsets import DjingModelViewSet
from groupapp.models import Group
from groupapp.serializers import GroupsSerializer # , SetRelatedPermsRecursiveSerializer
# from profiles.serializers import PermissionModelSerializer


class GroupsModelViewSets(DjingModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupsSerializer
    filter_backends = [CustomObjectPermissionsFilter, OrderingFilter]
    ordering_fields = 'title',

    # @action(detail=False)
    # def get_all_related_perms(self, request):
    #     if not request.user.is_superuser:
    #         return Response(status=status.HTTP_403_FORBIDDEN)
    #     related_perms_qs = Group.objects.get_perms4related_models()
    #
    #     serializer = PermissionModelSerializer(related_perms_qs, many=True)
    #     return Response(serializer.data)

    # @action(detail=True, methods=['put'])
    # def set_related_perms_recursive(self, request, pk=None):
    #     if not request.user.is_superuser:
    #         return Response(status=status.HTTP_403_FORBIDDEN)
    #     current_group = self.get_object()
    #
    #     serializer = SetRelatedPermsRecursiveSerializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #
    #     data = serializer.data
    #     perms = data.get('permission_ids', [])
    #     profile_group = get_object_or_404(ProfileGroup, pk=data.get('profile_group'))
    #
    #     r = current_group.set_permissions_recursive(
    #         permission_ids=perms,
    #         profile_group=profile_group
    #     )
    #     return Response('ok', status=status.HTTP_200_OK if r else status.HTTP_400_BAD_REQUEST)
