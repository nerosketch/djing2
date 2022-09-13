from dataclasses import dataclass

from customers.schemas import CustomerModelSchema
from rest_framework.generics import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response

from fastapi import APIRouter, Request, Depends
from djing2.lib.fastapi.auth import is_admin_auth_dependency
from djing2.lib.fastapi.crud import NOT_FOUND, CrudRouter
from . import schemas

from customers.serializers import CustomerModelSerializer
from customers.models import Customer
from customers_legal import models
from customers_legal import serializers
from djing2.viewsets import DjingModelViewSet
from dynamicfields.views import AbstractDynamicFieldContentModelViewSet


router = APIRouter(
    prefix='/legal',
    tags=['CustomerLegal'],
    dependencies=[Depends(is_admin_auth_dependency)]
)

router.include_router(CrudRouter(
    schema=schemas.CustomerLegalSchema,
    queryset=models.CustomerLegalModel.objects.all(),
    create_schema=schemas.CustomerLegalBaseSchema,
    update_schema=schemas.CustomerLegalBaseSchema
))


@dataclass
class LegalTypeItem:
    value: int
    label: str


@router.get('/get_legal_types/', response_model=list[LegalTypeItem])
def get_legal_types():
    res = ({'value': k, 'label': v} for k, v in models.CustomerLegalIntegerChoices.choices)
    return res


@router.get('/{legal_id}/get_branches/', response_model=list[CustomerModelSchema])
def get_branches(legal_id: int):
    qs = Customer.objects.filter(customerlegalmodel=pk)
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




class LegalCustomerBankModelViewSet(DjingModelViewSet):
    queryset = models.LegalCustomerBankModel.objects.all()
    serializer_class = serializers.LegalCustomerBankModelSerializer
    filterset_fields = ('legal_customer',)


class CustomerLegalTelephoneModelViewSet(DjingModelViewSet):
    queryset = models.CustomerLegalTelephoneModel.objects.all()
    serializer_class = serializers.CustomerLegalTelephoneModelSerializer

