from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser


class DjingModelViewSet(ModelViewSet):
    permission_classes = (IsAuthenticated, IsAdminUser)
