from rest_framework import viewsets
from rest_framework.generics import GenericAPIView, RetrieveAPIView

from profiles.models import UserProfile, UserProfileLog
from profiles.serializers import UserProfileSerializer, UserProfileLogSerializer
from djing2.metadata import FieldMetadata


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    metadata_class = FieldMetadata

    # FIXME: Only on development. Prevent CORS error in browser
    def dispatch(self, request, *args, **kwargs):
        r = super(UserProfileViewSet, self).dispatch(request, *args, **kwargs)
        r["Access-Control-Allow-Origin"] = "*"
        r["Access-Control-Allow-Methods"] = '*'
        return r


class UserProfileDetails(RetrieveAPIView):
    serializer_class = UserProfileSerializer


class UserProfileLogViewSet(viewsets.ModelViewSet):
    queryset = UserProfileLog.objects.all()
    serializer_class = UserProfileLogSerializer
    metadata_class = FieldMetadata


