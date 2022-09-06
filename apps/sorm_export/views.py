from datetime import datetime, timedelta

from django.db.models import Count
from djing2.lib.fastapi.crud import CRUDReadGenerator
from fastapi import APIRouter, Depends, Request
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from djing2.lib.mixins import SitesFilterMixin
from djing2.lib.fastapi.auth import is_admin_auth_dependency
from customers.models import Customer
from customers.serializers import CustomerModelSerializer
from customers import schemas as customers_schemas


router = APIRouter(
    prefix='/sorm',
    tags=['СОРМ'],
    dependencies=[Depends(is_admin_auth_dependency)]
)


class CustomerModelSchemaWLegals(customers_schemas.CustomerModelSchema):
    legals: int


router.include_router(CRUDReadGenerator(
    schema=CustomerModelSchemaWLegals,
    prefix='/passports',
    queryset=Customer.objects.annotate(
            legals=Count('customerlegalmodel')
        ).filter(
            passportinfo=None,
            legals=0,
            is_active=True
        )
))


class ContractsReadCRUD(CRUDReadGenerator):
    def _get_all(self, *args, **kwargs):
        ofn = super()._get_all(*args, **kwargs)

        def _rar(item_id: int, request: Request):
            """
            Fetch example:

            >>> import csv
            >>> import requests
            >>>
            >>>
            >>> r = requests.get('http://localhost:8000/api/sorm/contracts/', headers={
            >>>     'Authorization': 'Token ffffffffffffffffffffffffffffffffffff',
            >>>     'Content-type': 'application/json'
            >>> }, params={
            >>>     'fields': 'id,username,full_namevm ap'
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
            return ofn(item_id, request)

        return _rar

    # def _get_one(self, *args: Any, **kwargs: Any):
    #     pass


router.include_router(ContractsReadCRUD(
    schema=customers_schemas.CustomerModelSchema,
    prefix='/contracts',
    queryset=Customer.objects.annotate(
            ccc=Count('customercontractmodel'),
            legc=Count('customerlegalmodel')
        ).filter(
            ccc=0,
            legc=0,
            is_active=True
        ),
))


class SormCustomersTooOldView(SitesFilterMixin, ReadOnlyModelViewSet):
    queryset = Customer.objects.annotate(
        legals=Count('customerlegalmodel')
    ).filter(
        legals=0,
        is_active=True
    )
    serializer_class = CustomerModelSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        # 110 years
        too_old = datetime.now() - timedelta(days=40150)
        qs = super().get_queryset()
        return qs.filter(
            birth_day__lte=too_old
        )
