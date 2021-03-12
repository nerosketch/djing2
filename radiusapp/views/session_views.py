from rest_framework.decorators import action
from djing2.viewsets import DjingModelViewSet
from radiusapp.models import CustomerRadiusSession
from radiusapp.serializers.user_session import CustomerRadiusSessionModelSerializer


class CustomerRadiusSessionModelViewSet(DjingModelViewSet):
    queryset = CustomerRadiusSession.objects.all()
    serializer_class = CustomerRadiusSessionModelSerializer
    filterset_fields = ['customer', 'radius_username', 'closed']

    @action(methods=['get'], detail=False)
    def guest_list(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter(customer=None)
        return self.list(request, *args, **kwargs)
