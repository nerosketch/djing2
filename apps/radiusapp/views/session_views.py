from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from djing2.viewsets import DjingModelViewSet
from djing2.lib import safe_int
from radiusapp.models import CustomerRadiusSession
from radiusapp.serializers.user_session import CustomerRadiusSessionModelSerializer
from radiusapp import tasks


class CustomerRadiusSessionModelViewSet(DjingModelViewSet):
    queryset = CustomerRadiusSession.objects.all()
    serializer_class = CustomerRadiusSessionModelSerializer
    filterset_fields = ["customer", "radius_username", "closed"]

    @action(methods=["get"], detail=False)
    def guest_list(self, request, *args, **kwargs):
        self.queryset = self.queryset.filter(customer=None)
        return self.list(request, *args, **kwargs)

    @action(methods=["get"], detail=False, url_path=r"get_by_lease/(?P<lease_id>\d{1,18})")
    def get_by_lease(self, request, lease_id=None, *args, **kwargs):
        lease_id = safe_int(lease_id)
        if lease_id <= 0:
            return Response(status=status.HTTP_404_NOT_FOUND)
        sessions = CustomerRadiusSession.objects.filter(ip_lease_id=lease_id)
        if sessions.exists():
            serializer = self.get_serializer(instance=sessions.first())
            return Response(serializer.data)
        return Response()

    def destroy(self, request, *args, **kwargs):
        session = self.get_object()
        tasks.async_finish_session_task(radius_uname=session.radius_username)
        return super().destroy(request, *args, **kwargs)
