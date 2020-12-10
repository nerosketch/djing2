from rest_framework.viewsets import ModelViewSet

from radiusapp.models import UserSession
from radiusapp.serializers.user_session import UserSessionModelSerializer


class UserSessionModelViewSet(ModelViewSet):
    queryset = UserSession.objects.all()
    serializer_class = UserSessionModelSerializer
    filterset_fields = ['customer', 'radius_username', 'closed']
