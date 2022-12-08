from typing import Optional
from customer_contract import models
from djing2.lib.fastapi.auth import is_admin_auth_dependency
from djing2.lib.fastapi.crud import CrudRouter
from djing2.lib.fastapi.pagination import paginate_qs_path_decorator
from djing2.lib.fastapi.perms import permission_check_dependency
from djing2.lib.fastapi.types import IListResponse, Pagination, NOT_FOUND
from djing2.lib.fastapi.utils import create_get_initial_route
from fastapi import APIRouter, Depends, Request, Path, UploadFile, Form
from profiles.models import UserProfile
from starlette import status

from . import schemas


router = APIRouter(
    prefix='/customer_contract',
    tags=['CustomerContracts'],
    dependencies=[Depends(is_admin_auth_dependency)]
)


@router.get('/contract/',
            response_model=IListResponse[schemas.CustomerContractSchema],
            dependencies=[Depends(
                permission_check_dependency(
                    perm_codename='customer_contract.view_customercontractmodel'
                )
            )])
@paginate_qs_path_decorator(
    schema=schemas.CustomerContractSchema,
    db_model=models.CustomerContractModel
)
def get_contracts(
    request: Request,
    pagination: Pagination = Depends(),
    customer: Optional[int] = None):
    _base_contr_qs = models.CustomerContractModel.objects.all()
    if customer is not None:
        return _base_contr_qs.filter(customer_id=customer)
    return _base_contr_qs


@router.post('/contract/',
             response_model=schemas.CustomerContractSchema,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(
                 permission_check_dependency(
                     perm_codename='customer_contract.add_customercontractmodel'
                 )
             )])
def new_contract_route(contract_data: schemas.CustomerContractBaseSchema):
    new_contract = models.CustomerContractModel.objects.create(**contract_data.dict())
    return schemas.CustomerContractSchema.from_orm(new_contract)


@router.delete('/contract/{contract_id}/',
               status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(
                   permission_check_dependency(
                       perm_codename='customer_contract.delete_customercontractmodel'
                   )
               )])
def del_contract(contract_id: int):
    c = models.CustomerContractModel.objects.filter(pk=contract_id)
    if not c.exists():
        raise NOT_FOUND
    c.delete()


@router.patch('/contract/{contract_id}/',
              response_model=schemas.CustomerContractSchema,
              dependencies=[Depends(
                  permission_check_dependency(
                      perm_codename='customer_contract.change_customercontractmodel'
                  )
              )])
def change_contract(contract_data: schemas.CustomerContractBaseSchema,
                    contract_id: int = Path(gt=0)
                    ):
    c = models.CustomerContractModel.objects.filter(pk=contract_id)
    if not c.exists():
        raise NOT_FOUND
    c.update(**contract_data.dict())
    return schemas.CustomerContractSchema.from_orm(c.first())


@router.put('/contract/{contract_id}/finish/',
            response_model=schemas.CustomerContractSchema,
            dependencies=[Depends(
                permission_check_dependency(
                    perm_codename='customer_contract.change_customercontractmodel'
                )
            )])
def finish_contract(contract_id: int):
    contract = models.CustomerContractModel.objects.get(pk=contract_id)
    contract.finish()
    return schemas.CustomerContractSchema.from_orm(contract)


router.include_router(CrudRouter(
    schema=schemas.CustomerContractAttachmentSchema,
    queryset=models.CustomerContractAttachmentModel.objects.all(),
    create_route=False,
    update_route=False
), prefix='/docs')


@router.post('/docs/',
             response_model=schemas.CustomerContractAttachmentSchema)
def create_contract_attachment(
    doc_file: UploadFile,
    title: str = Form(),
    contract_id: int = Form(gt=0),
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='customer_contract.add_customercontractattachmentmodel'
    ))
):
    from django.core.files.base import ContentFile
    df = ContentFile(doc_file.file._file.read(), name=doc_file.filename)
    new_attachment = models.CustomerContractAttachmentModel.objects.create(
        contract_id=contract_id,
        author=curr_user,
        title=title,
        doc_file=df
    )
    return schemas.CustomerContractAttachmentSchema.from_orm(new_attachment)


create_get_initial_route(
    router=router,
    path='/contract/get_initial/',
    schema=schemas.CustomerContractBaseSchema
)
