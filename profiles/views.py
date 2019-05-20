from djing2.viewsets import DjingModelViewSet
from profiles.models import UserProfile, UserProfileLog
from profiles.serializers import UserProfileSerializer, UserProfileLogSerializer
from djing2.metadata import FieldMetadata


class UserProfileViewSet(DjingModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    metadata_class = FieldMetadata
    lookup_field = 'username'


class UserProfileLogViewSet(DjingModelViewSet):
    queryset = UserProfileLog.objects.all()
    serializer_class = UserProfileLogSerializer
    metadata_class = FieldMetadata
