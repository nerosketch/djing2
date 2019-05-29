from django.db import IntegrityError
from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from djing2.exceptions import UniqueConstraintIntegrityError


class DjingModelViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated, IsAdminUser)

    def perform_create(self, serializer):
        try:
            return super().perform_create(serializer)
        except IntegrityError as e:
            raise UniqueConstraintIntegrityError(e)
