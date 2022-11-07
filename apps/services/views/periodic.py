from customers.models import Customer
from djing2.lib.fastapi.auth import is_admin_auth_dependency, TOKEN_RESULT_TYPE
from djing2.lib.fastapi.crud import CrudRouter
from djing2.lib.fastapi.pagination import paginate_qs_path_decorator
from djing2.lib.fastapi.perms import filter_qs_by_rights
from djing2.lib.fastapi.types import IListResponse, Pagination
from fastapi import APIRouter, Depends, Request
from services import models
from services import schemas

router = APIRouter(
    prefix='/periodic-pay',
    dependencies=[Depends(is_admin_auth_dependency)]
)

router.include_router(CrudRouter(
    schema=schemas.PeriodicPayForIdModelSchema,
    create_schema=schemas.PeriodicPayForIdBaseSchema,
    queryset=models.PeriodicPayForId.objects.defer("account").select_related("periodic_pay"),
    get_all_route=False
))


@router.get('',
            response_model=IListResponse[schemas.PeriodicPayForIdModelSchema],
            response_model_exclude_none=True
            )
@paginate_qs_path_decorator(
    schema=schemas.PeriodicPayForIdModelSchema,
    db_model=models.PeriodicPayForId
)
def get_periodic_pays(request: Request, account: int,
                      auth: TOKEN_RESULT_TYPE = Depends(is_admin_auth_dependency),
                      pagination: Pagination = Depends(),
                      ):
    curr_user, token = auth

    rqs = filter_qs_by_rights(
        qs_or_model=Customer.objects.filter(pk=account),
        curr_user=curr_user,
        perm_codename='customers.view_customer'
    )
    qs = models.PeriodicPayForId.objects.filter(
        account_id__in=rqs
    )
    return qs
