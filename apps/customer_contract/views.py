from typing import Optional
from customer_contract import models
from djing2.lib.fastapi.auth import is_admin_auth_dependency
from djing2.lib.fastapi.crud import NOT_FOUND, CrudRouter
from djing2.lib.fastapi.pagination import paginate_qs_path_decorator
from djing2.lib.fastapi.perms import permission_check_dependency
from djing2.lib.fastapi.types import IListResponse, Pagination
from djing2.lib.fastapi.utils import create_get_initial_route
from fastapi import APIRouter, Depends, Request
from starlette import status

from . import schemas


router = APIRouter(
    prefix='/customer_contract',
    tags=['CustomerContracts'],
    dependencies=[Depends(is_admin_auth_dependency)]
)

_base_contr_qs = models.CustomerContractModel.objects.all()


@router.get('/contract/', response_model=IListResponse[schemas.CustomerContractSchema], dependencies=[Depends(
    permission_check_dependency(perm_codename='customer_contract.view_customercontractmodel')
)])
@paginate_qs_path_decorator(schema=schemas.CustomerContractSchema, db_model=models.CustomerContractModel)
def get_contracts(
    request: Request,
    pagination: Pagination = Depends(),
    customer: Optional[int] = None):
    if customer is not None:
        return _base_contr_qs.filter(customer_id=customer)
    return _base_contr_qs


@router.post('/contract/', response_model=schemas.CustomerContractSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(
    permission_check_dependency(perm_codename='customer_contract.add_customercontractmodel')
)])
def new_contract_route(contract_data: schemas.CustomerContractBaseSchema):
    new_contract = models.CustomerContractModel.objects.create(**contract_data.dict())
    return schemas.CustomerContractSchema.from_orm(new_contract)


@router.delete('/contract/{contract_id}/', status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(
    permission_check_dependency(perm_codename='customer_contract.delete_customercontractmodel')
)])
def del_contract(contract_id: int):
    c = models.CustomerContractModel.objects.filter(pk=contract_id)
    if not c.exists():
        raise NOT_FOUND
    c.delete()


@router.patch('/contract/{contract_id}/', response_model=schemas.CustomerContractSchema, dependencies=[Depends(
    permission_check_dependency(perm_codename='customer_contract.change_customercontractmodel')
)])
def change_contract(contract_id: int, contract_data: schemas.CustomerContractBaseSchema):
    c = models.CustomerContractModel.objects.filter(pk=contract_id)
    if not c.exists():
        raise NOT_FOUND
    c.update(**contract_data.dict())
    return schemas.CustomerContractSchema.from_orm(c)


@router.put('/contract/{contract_id}/finish/', response_model=schemas.CustomerContractSchema, dependencies=[Depends(
    permission_check_dependency(perm_codename='customer_contract.change_customercontractmodel')
)])
def finish_contract(contract_id: int):
    contract = models.CustomerContractModel.objects.get(pk=contract_id)
    contract.finish()
    return schemas.CustomerContractSchema.from_orm(contract)


router.include_router(CrudRouter(
    schema=schemas.CustomerContractAttachmentSchema,
    create_schema=schemas.CustomerContractAttachmentBaseSchema,
    queryset=models.CustomerContractAttachmentModel.objects.all()
), prefix='/docs')


create_get_initial_route(
    router=router,
    path='/contract/get_initial/',
    schema=schemas.CustomerContractBaseSchema
)
