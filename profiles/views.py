from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.viewsets import DjingModelViewSet
from profiles.models import UserProfile, UserProfileLog
from profiles.serializers import UserProfileSerializer, UserProfileLogSerializer


class UserProfileViewSet(DjingModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    lookup_field = 'username'

    @action(detail=False, url_path='get_responsibilities/(?P<group_id>\d{1,9})')
    def get_responsibilities_for_group(self, request, group_id: str):
        profile_ids = UserProfile.objects.get_profiles_by_group(group_id).values_list('pk')
        return Response(data=(pi[0] for pi in profile_ids))


class UserProfileLogViewSet(DjingModelViewSet):
    queryset = UserProfileLog.objects.all()
    serializer_class = UserProfileLogSerializer
