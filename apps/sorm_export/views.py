from django.db.models import Count
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated
from djing2.permissions import IsSuperUser
from customers.models import Customer
from customers.serializers import CustomerModelSerializer


class SormCustomersWithoutContractsListView(ReadOnlyModelViewSet):
    """
    Fetch example:

    >>> import csv
    >>> import requests
    >>>
    >>>
    >>> r = requests.get('http://localhost:8000/api/sorm/', headers={
    >>>     'Authorization': 'Token ffffffffffffffffffffffffffffffffffff',
    >>>     'Content-type': 'application/json'
    >>> }, params={
    >>>     'fields': 'id,username,full_name'
    >>> })
    >>>
    >>> customers = r.json()
    >>>
    >>> with open('customers_without_contracts.csv', 'w') as f:
    >>>     writer = csv.DictWriter(f, fieldnames=['id', 'логин', 'фио'])
    >>>     writer.writeheader()
    >>>     for customer in customers:
    >>>         vals = {
    >>>             'id': customer.get('id'),
    >>>             'логин': customer.get('username'),
    >>>             'фио': customer.get('full_name')
    >>>         }
    >>>         writer.writerow(vals)
    >>>
    """
    queryset = Customer.objects.annotate(
        ccc=Count('customercontractmodel')
    ).filter(
        ccc=0,
        is_active=True
    )
    serializer_class = CustomerModelSerializer
    permission_classes = [IsAuthenticated, IsSuperUser]

