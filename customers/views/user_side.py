from customers import serializers
from customers import models
from djing2.viewsets import BaseNonAdminReadOnlyModelViewSet


class CustomersReadOnlyModelViewSet(BaseNonAdminReadOnlyModelViewSet):
    queryset = models.Customer.objects.all()
    serializer_class = serializers.CustomerModelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(username=self.request.user.username)


class LogsReadOnlyModelViewSet(BaseNonAdminReadOnlyModelViewSet):
    queryset = models.CustomerLog.objects.all()
    serializer_class = serializers.CustomerLogModelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(customer=self.request.user)

