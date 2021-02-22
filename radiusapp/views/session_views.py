from djing2.viewsets import DjingModelViewSet
from radiusapp.models import CustomerRadiusSession
from radiusapp.serializers.user_session import CustomerRadiusSessionModelSerializer


class CustomerRadiusSessionModelViewSet(DjingModelViewSet):
    queryset = CustomerRadiusSession.objects.all()
    serializer_class = CustomerRadiusSessionModelSerializer
    filterset_fields = ['customer', 'radius_username', 'closed']
