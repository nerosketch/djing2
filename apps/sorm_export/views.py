from datetime import datetime, timedelta
from django.db.models import Count
from djing2.lib.fastapi.pagination import Pagination, paginate_qs_path_decorator
from fastapi import APIRouter, Depends, Request
from djing2.lib.fastapi.auth import is_admin_auth_dependency
from djing2.lib.fastapi.types import IListResponse
from customers.models import Customer
from customers import schemas as customers_schemas


router = APIRouter(
    prefix='/sorm',
    tags=['СОРМ'],
    dependencies=[Depends(is_admin_auth_dependency)]
)


@router.get('/passports/', response_model=IListResponse[customers_schemas.CustomerModelSchema])
@paginate_qs_path_decorator(schema=customers_schemas.CustomerModelSchema, db_model=Customer)
def get_bad_passports(request: Request, pagination: Pagination = Depends()):
    qs = Customer.objects.annotate(
        legals=Count('customerlegalmodel')
    ).filter(
        passportinfo=None,
        legals=0,
        is_active=True
    )
    return qs


@router.get('/contracts/', response_model=IListResponse[customers_schemas.CustomerModelSchema])
@paginate_qs_path_decorator(schema=customers_schemas.CustomerModelSchema, db_model=Customer)
def get_contracts(request: Request, pagination: Pagination = Depends()):
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
    qs = Customer.objects.annotate(
        ccc=Count('customercontractmodel'),
        legc=Count('customerlegalmodel')
    ).filter(
        ccc=0,
        legc=0,
        is_active=True
    )
    return qs


@router.get('/birth_day/', response_model=IListResponse[customers_schemas.CustomerModelSchema])
@paginate_qs_path_decorator(schema=customers_schemas.CustomerModelSchema, db_model=Customer)
def get_without_birth_day(request: Request, pagination: Pagination = Depends()):
    years_ago_110 = datetime.now() - timedelta(days=40150)
    too_old_customers_qs = Customer.objects.annotate(
        legals=Count('customerlegalmodel')
    ).filter(
        legals=0,
        is_active=True,
        birth_day__lte=years_ago_110
    )
    return too_old_customers_qs
