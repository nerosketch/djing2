from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.response import Response

from djing2.viewsets import DjingModelViewSet
from profiles.models import UserProfile, UserProfileLog
from profiles.serializers import UserProfileSerializer, UserProfileLogSerializer


class CustomObtainAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        if not isinstance(user, UserProfile):
            return Response({
                'text': _('Login is not possible')
            }, status=status.HTTP_403_FORBIDDEN)
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})


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
