from django.contrib.sites.models import Site
from django.db import transaction
from djing2.lib.fastapi.general_filter import general_filter_queryset
from djing2.lib.fastapi.perms import permission_check_dependency
from djing2.lib.fastapi.sites_depend import sites_dependency
from djing2.lib.fastapi.utils import get_object_or_404
from fastapi import APIRouter, Depends, Response
from profiles.models import UserProfile
from customers.models import Customer
from starlette import status
from djing2.lib.fastapi.auth import is_admin_auth_dependency
from djing2.lib.fastapi.crud import CrudRouter
from services import schemas
from services import models


router = APIRouter(
    dependencies=[Depends(is_admin_auth_dependency)]
)


@router.post('/{customer_id}/make_shot/', responses={
    status.HTTP_403_FORBIDDEN: {
        'description': 'making payment shot not possible'
    },
    status.HTTP_200_OK: {
        'description': 'Payment shot provided successfully'
    }
})
def make_payment_shot(customer_id: int, payload: schemas.MakePaymentSHotRequestSchema,
                      curr_site: Site = Depends(sites_dependency),
                      curr_user: UserProfile = Depends(permission_check_dependency(
                          perm_codename='customers.can_buy_service'
                      ))
                      ):
    customers_queryset = general_filter_queryset(
        qs_or_model=Customer,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='customers.can_buy_service'
    )
    customer = get_object_or_404(customers_queryset, pk=customer_id)

    shot_queryset = general_filter_queryset(
        qs_or_model=models.OneShotPay,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='services.view_oneshotpay'
    )
    shot = get_object_or_404(shot_queryset, pk=payload.shot_id)

    shot.before_pay(customer=customer)
    r = customer.pick4customer(
        shot=shot,
        user_profile=curr_user,
        allow_negative=True
    )
    shot.after_pay(customer=customer)
    if not r:
        return Response(status_code=status.HTTP_403_FORBIDDEN)
    return Response(r)


router.include_router(CrudRouter(
    schema=schemas.OneShotPayModelSchema,
    update_schema=schemas.OneShotPayBaseSchema,
    queryset=models.OneShotPay.objects.all(),
    create_route=False,
), prefix='/shot')


@router.post('/shot/',
             response_model=schemas.OneShotPayModelSchema,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(permission_check_dependency(
                 perm_codename='services.add_oneshotpay'
             ))]
             )
def create_periodic_pay(payload: schemas.OneShotPayBaseSchema,
                        curr_site: Site = Depends(sites_dependency),
                        ):
    with transaction.atomic():
        new_op = models.OneShotPay.objects.create(
            **payload.dict()
        )
        new_op.sites.add(curr_site)
    return schemas.OneShotPayModelSchema.from_orm(new_op)


