from typing import Optional

from customers.models import Customer
from customers.schemas import CustomerModelSchema
from customers_legal import models
from djing2.lib.fastapi.auth import is_admin_auth_dependency
from djing2.lib.fastapi.crud import CrudRouter
from djing2.lib.fastapi.perms import permission_check_dependency
from djing2.lib.fastapi.utils import create_get_initial_route
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from . import schemas

router = APIRouter(
    prefix='/legal',
    tags=['CustomerLegal'],
    dependencies=[Depends(is_admin_auth_dependency)]
)


@router.get('/{legal_id}/get_branches/', response_model=list[CustomerModelSchema], dependencies=[Depends(
    permission_check_dependency(perm_codename='customers.view_customer')
)])
def get_branches(legal_id: int):
    qs = Customer.objects.filter(customerlegalmodel=legal_id)
    return (CustomerModelSchema.from_orm(c) for c in qs)


class LegalTypeItem(BaseModel):
    value: int
    label: str


@router.get('/get_legal_types/', response_model=list[LegalTypeItem])
def get_legal_types():
    res = (LegalTypeItem(value=k, label=str(v)) for k, v in models.CustomerLegalIntegerChoices.choices)
    return res


router.include_router(CrudRouter(
    schema=schemas.LegalCustomerBankSchema,
    queryset=models.LegalCustomerBankModel.objects.all(),
    create_schema=schemas.LegalCustomerBankBaseSchema,
    get_all_route=False
), prefix='/bank')


@router.get('/bank/', response_model=list[schemas.LegalCustomerBankSchema], dependencies=[Depends(
    permission_check_dependency(perm_codename='customers_legal.view_legalcustomerbankmodel')
)])
def get_all_banks(legal_customer: Optional[int] = None):
    qs = models.LegalCustomerBankModel.objects.all()
    if legal_customer is not None:
        qs = qs.filter(legal_customer_id=legal_customer)
    return (schemas.LegalCustomerBankSchema.from_orm(i) for i in qs)


router.include_router(CrudRouter(
    schema=schemas.CustomerLegalTelephoneSchema,
    queryset=models.CustomerLegalTelephoneModel.objects.all(),
    create_schema=schemas.CustomerLegalTelephoneBaseSchema
), prefix='/telephone')


create_get_initial_route(
    router=router,
    schema=schemas.CustomerLegalSchema
)

router.include_router(CrudRouter(
    schema=schemas.CustomerLegalSchema,
    queryset=models.CustomerLegalModel.objects.all(),
    create_schema=schemas.CustomerLegalBaseSchema
))
