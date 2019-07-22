from djing2.viewsets import DjingModelViewSet
from profiles.models import UserProfile, UserProfileLog
from profiles.serializers import UserProfileSerializer, UserProfileLogSerializer


class UserProfileViewSet(DjingModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    lookup_field = 'username'


class UserProfileLogViewSet(DjingModelViewSet):
    queryset = UserProfileLog.objects.all()
    serializer_class = UserProfileLogSerializer
