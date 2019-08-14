from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from customers.serializers import CustomerModelSerializer
from customers import models


class BaseCustomersReadOnlyModelViewSet(ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)


class CustomersReadOnlyModelViewSet(BaseCustomersReadOnlyModelViewSet):
    queryset = models.Customer.objects.all()
    serializer_class = CustomerModelSerializer
