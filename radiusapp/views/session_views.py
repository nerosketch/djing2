from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from djing2.viewsets import DjingModelViewSet
from radiusapp.models import CustomerRadiusSession
from radiusapp.serializers.user_session import CustomerRadiusSessionModelSerializer


class CustomerRadiusSessionModelViewSet(DjingModelViewSet):
    queryset = CustomerRadiusSession.objects.all()
    serializer_class = CustomerRadiusSessionModelSerializer
    filterset_fields = ['customer', 'radius_username', 'closed']

    @action(methods=['get'], detail=True)
    def destroy_session(self, request, pk=None):
        session = self.get_object()
        if session.finish_session():
            session.delete()
            return Response('ok')
        return Response('fail', status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(methods=['get'], detail=False)
    def guest_list(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter(customer=None)
        return self.list(request, *args, **kwargs)
