from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from customers import serializers
from customers import models


class BaseCustomersReadOnlyModelViewSet(ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)


class CustomersReadOnlyModelViewSet(BaseCustomersReadOnlyModelViewSet):
    queryset = models.Customer.objects.all()
    serializer_class = serializers.CustomerModelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(username=self.request.user.username)


class LogsReadOnlyModelViewSet(BaseCustomersReadOnlyModelViewSet):
    queryset = models.CustomerLog.objects.all()
    serializer_class = serializers.CustomerLogModelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(customer=self.request.user)

