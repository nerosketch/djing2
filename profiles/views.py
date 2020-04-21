from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from djing2.viewsets import DjingModelViewSet, BaseNonAdminReadOnlyModelViewSet
from profiles.models import UserProfile, UserProfileLog
from profiles.serializers import UserProfileSerializer, UserProfileLogSerializer


class UserProfileViewSet(DjingModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    lookup_field = 'username'

    @action(detail=False, url_path='get_profiles_by_group/(?P<group_id>\d{1,9})')
    def get_profiles_by_group(self, request, group_id: str):
        profile_ids = UserProfile.objects.get_profiles_by_group(group_id).values_list('pk')
        return Response(data=(pi[0] for pi in profile_ids))

    @action(detail=True, methods=('get',))
    def get_responsibility_groups(self, request, username=None):
        profile = self.get_object()
        group_ids = tuple(g[0] for g in profile.responsibility_groups.all().values_list('pk'))
        return Response(group_ids)

    @action(detail=True, methods=('put',))
    def set_responsibility_groups(self, request, username=None):
        profile = self.get_object()

        checked_groups = (int(gi) for gi in request.data.get('groups'))
        # profile.responsibility_groups.clear()
        profile.responsibility_groups.set(checked_groups)
        return Response()


class UserProfileLogViewSet(DjingModelViewSet):
    queryset = UserProfileLog.objects.all()
    serializer_class = UserProfileLogSerializer


class LocationAuth(APIView):
    throttle_classes = ()
    permission_classes = ()

    def get(self, request, *args, **kwargs):
        user = authenticate(
            request=request,
            byip=True
        )

        if not user:
            msg = _('Unable to log in with provided credentials.')
            raise ValidationError(msg, code='authorization')

        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})


class CurrentAuthenticatedProfileROViewSet(BaseNonAdminReadOnlyModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer

    def get_object(self):
        return UserProfile.objects.get(pk=self.request.user.pk)

    def list(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(pk=self.request.user.pk)
