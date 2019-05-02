from rest_framework import viewsets
from rest_framework.generics import RetrieveUpdateDestroyAPIView

from djing2.custom_mixins import CorsAllow
from profiles.models import UserProfile, UserProfileLog
from profiles.serializers import UserProfileSerializer, UserProfileLogSerializer
from djing2.metadata import FieldMetadata


class UserProfileViewSet(CorsAllow, viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    metadata_class = FieldMetadata


class UserProfileDetails(CorsAllow, RetrieveUpdateDestroyAPIView):
    model = UserProfile
    lookup_field = 'username'
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer


class UserProfileLogViewSet(viewsets.ModelViewSet):
    queryset = UserProfileLog.objects.all()
    serializer_class = UserProfileLogSerializer
    metadata_class = FieldMetadata
