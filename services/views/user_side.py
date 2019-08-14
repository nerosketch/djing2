from djing2.viewsets import BaseNonAdminReadOnlyModelViewSet
from services.models import Service
from services import serializers


class UserSideServiceModelViewSet(BaseNonAdminReadOnlyModelViewSet):
    queryset = Service.objects.filter(is_admin=False)
    serializer_class = serializers.ServiceModelSerializer
    qs_cache = None

    def get_queryset(self):
        if self.qs_cache is not None:
            return self.qs_cache
        qs = super().get_queryset()
        eqs = Service.objects.none()
        current_user = self.request.user
        if not current_user:
            return eqs
        user_grp = current_user.group
        if not user_grp:
            return eqs
        self.qs_cache = qs.filter(groups__in=(user_grp,))
        return self.qs_cache
