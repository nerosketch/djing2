from customers.models import Customer
from django.contrib.sites.models import Site
from djing2.lib.fastapi.auth import is_admin_auth_dependency, TOKEN_RESULT_TYPE
from djing2.lib.fastapi.crud import CrudRouter
from djing2.lib.fastapi.general_filter import general_filter_queryset
from djing2.lib.fastapi.pagination import paginate_qs_path_decorator
from djing2.lib.fastapi.perms import filter_qs_by_rights, permission_check_dependency
from djing2.lib.fastapi.sites_depend import sites_dependency
from djing2.lib.fastapi.types import IListResponse, Pagination
from djing2.lib.fastapi.utils import get_object_or_404
from fastapi import APIRouter, Depends, Request, Response
from profiles.models import UserProfile
from services import models
from services import schemas

router = APIRouter(
    prefix='/periodic-pay',
    dependencies=[Depends(is_admin_auth_dependency)]
)


@router.post('/{customer_id}/make_periodic_pay/')
def make_periodic_pay(
    customer_id: int,
    payload: schemas.PeriodicPayForIdRequestSchema,
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='customers.can_buy_service'
    )),
    curr_site: Site = Depends(sites_dependency)
):
    customers_queryset = general_filter_queryset(
        qs_or_model=Customer,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.can_buy_service'
    )
    customer = get_object_or_404(
        customers_queryset,
        pk=customer_id
    )

    pp_queryset = general_filter_queryset(
        qs_or_model=models.PeriodicPay,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.view_periodicpay'
    )
    periodic_pay = get_object_or_404(
        pp_queryset,
        pk=payload.periodic_pay_id
    )
    customer.make_periodic_pay(
        periodic_pay=periodic_pay,
        next_pay=payload.next_pay
    )
    return Response("ok")


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
