from addresses.models import AddressModel
from customers.models import Customer
from django.contrib.postgres.aggregates.general import ArrayAgg
from django.db.models.aggregates import Count
from djing2.lib.fastapi.auth import is_superuser_auth_dependency
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter(
    prefix='/customer_duplicates',
    tags=['CustomerDuplicates'],
    dependencies=[Depends(is_superuser_auth_dependency)]
)


class DuplicateResult(BaseModel):
    customer_count: int
    address: int
    address_full_title: str
    address_title: str
    customer_ids: list[int]


@router.get('/', response_model=list[DuplicateResult])
def get_all_address_duplicates(minimum_duplications: int = 2):
    """Get all customers with same addresses"""
    qs = Customer.objects.values('address', 'address__title').annotate(
        customer_count=Count('address'),
        customer_ids=ArrayAgg('pk')
    ).filter(customer_count__gte=minimum_duplications)
    for c in qs.iterator():
        addr_title = AddressModel.objects.get_address_full_title(
            c['address']
        )
        yield DuplicateResult(**c, address_full_title=addr_title, address_title=c['address__title'])
