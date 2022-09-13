from dataclasses import dataclass
from typing import Optional

from customers.models import Customer
from customers.schemas import CustomerModelSchema
from customers_legal import models
from djing2.lib.fastapi.auth import is_admin_auth_dependency
from djing2.lib.fastapi.crud import CrudRouter
from djing2.lib.fastapi.pagination import paginate_qs_path_decorator
from djing2.lib.fastapi.perms import permission_check_dependency
from djing2.lib.fastapi.types import IListResponse
from dynamicfields.views import AbstractDynamicFieldContentModelViewSet
from fastapi import APIRouter, Depends
from rest_framework.generics import get_object_or_404

from . import schemas

router = APIRouter(
    prefix='/legal',
    tags=['CustomerLegal'],
    dependencies=[Depends(is_admin_auth_dependency)]
)

router.include_router(CrudRouter(
    schema=schemas.CustomerLegalSchema,
    queryset=models.CustomerLegalModel.objects.all(),
    create_schema=schemas.CustomerLegalBaseSchema
))


@dataclass
class LegalTypeItem:
    value: int
    label: str


@router.get('/get_legal_types/', response_model=list[LegalTypeItem])
def get_legal_types():
    res = ({'value': k, 'label': v} for k, v in models.CustomerLegalIntegerChoices.choices)
    return res


@router.get('/{legal_id}/get_branches/', response_model=list[CustomerModelSchema], dependencies=[Depends(
    permission_check_dependency(perm_codename='customers.view_customer')
)])
def get_branches(legal_id: int):
    qs = Customer.objects.filter(customerlegalmodel=legal_id)
    return (CustomerModelSchema.from_orm(c) for c in qs)


class CustomerLegalDynamicFieldContentModelViewSet(AbstractDynamicFieldContentModelViewSet):
    queryset = models.CustomerLegalDynamicFieldContentModel.objects.all()

    def get_group_id(self) -> int:
        legal_customer_id = self.request.query_params.get('legal_customer_id')
        self.legal_customer_id = legal_customer_id
        legal_customer = get_object_or_404(models.CustomerLegalModel.objects.only('group_id'), pk=legal_customer_id)
        self.legal_customer = legal_customer
        return legal_customer.group_id

    def filter_content_fields_queryset(self):
        return self.get_queryset().objects.filter(
            legal_customer_id=self.legal_customer_id
        )

    def create_content_field_kwargs(self, field_data):
        if hasattr(self, 'legal_id'):
            return {
                'legal_customer_id': self.legal_customer_id
            }
        return {
            'legal_customer_id': field_data.get('legal_customer')
        }


router.include_router(CrudRouter(
    schema=schemas.LegalCustomerBankSchema,
    queryset=models.LegalCustomerBankModel.objects.all(),
    create_schema=schemas.LegalCustomerBankBaseSchema,
    get_all_route=False
), prefix='/bank')


@router.get('/bank/', response_model=IListResponse[schemas.LegalCustomerBankSchema], dependencies=[Depends(
    permission_check_dependency(perm_codename='customers_legal.view_legalcustomerbankmodel')
)])
@paginate_qs_path_decorator(schema=schemas.LegalCustomerBankSchema, db_model=models.LegalCustomerBankModel)
def get_all_banks(legal_customer: Optional[int] = None):
    qs = models.LegalCustomerBankModel.objects.all()
    if legal_customer is not None:
        qs = qs.filter(legal_customer_id=legal_customer)
    return qs


router.include_router(CrudRouter(
    schema=schemas.CustomerLegalTelephoneSchema,
    queryset=models.CustomerLegalTelephoneModel.objects.all(),
    create_schema=schemas.CustomerLegalTelephoneBaseSchema
))
