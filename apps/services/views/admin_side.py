from typing import Optional

from django.contrib.sites.models import Site
from django.db import transaction
from django.db.models.aggregates import Count
from djing2.lib.fastapi.auth import is_admin_auth_dependency
from djing2.lib.fastapi.crud import CrudRouter
from djing2.lib.fastapi.general_filter import general_filter_queryset
from djing2.lib.fastapi.pagination import paginate_qs_path_decorator
from djing2.lib.fastapi.perms import permission_check_dependency
from djing2.lib.fastapi.sites_depend import sites_dependency
from djing2.lib.fastapi.types import IListResponse, Pagination
from djing2.lib.fastapi.utils import get_object_or_404
from fastapi import APIRouter, Depends, Request, Path
from profiles.models import UserProfileLogActionType, UserProfile
from services import schemas
from services.models import Service, PeriodicPay, OneShotPay
from starlette import status

router = APIRouter(
    prefix='',
    dependencies=[Depends(is_admin_auth_dependency)]
)

router.include_router(CrudRouter(
    schema=schemas.PeriodicPayModelSchema,
    update_schema=schemas.PeriodicPayModelSchema,
    queryset=PeriodicPay.objects.all(),
    create_route=False,
), prefix='/periodic')


@router.post('/periodic/',
             response_model=schemas.PeriodicPayModelSchema,
             status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(permission_check_dependency(
                 perm_codename='services.add_periodicpay'
             ))]
             )
def create_periodic_pay(payload: schemas.PeriodicPayModelSchema,
                        curr_site: Site = Depends(sites_dependency),
                        ):
    with transaction.atomic():
        new_pp = PeriodicPay.objects.create(
            **payload.dict()
        )
        new_pp.sites.add(curr_site)
    return schemas.PeriodicPayModelSchema.from_orm(new_pp)


router.include_router(CrudRouter(
    schema=schemas.OneShotPayModelSchema,
    update_schema=schemas.OneShotPayBaseSchema,
    queryset=OneShotPay.objects.all(),
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
        new_op = OneShotPay.objects.create(
            **payload.dict()
        )
        new_op.sites.add(curr_site)
    return schemas.OneShotPayModelSchema.from_orm(new_op)


@router.patch('/{service_id}/',
              response_model=schemas.ServiceModelSchema
              )
def update_service(
    service_data: schemas.ServiceModelBaseSchema,
    service_id: int = Path(gt=0),
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='services.change_service'
    )),
    curr_site: Site = Depends(sites_dependency),
):
    services_qs = general_filter_queryset(
        qs_or_model=Service,
        curr_site=curr_site,
        curr_user=curr_user,
        perm_codename='services.change_service'
    )
    srv = get_object_or_404(services_qs, pk=service_id)
    pdata = service_data.dict(exclude_unset=True)

    for d_name, d_val in pdata.items():
        setattr(srv, d_name, d_val)

    srv.save(update_fields=[d_name for d_name, d_val in pdata.items()])
    return schemas.ServiceModelSchema.from_orm(srv)


@router.delete('/{service_id}/', status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def remove_service(service_id: int = Path(gt=0),
                   curr_site: Site = Depends(sites_dependency),
                   curr_user: UserProfile = Depends(permission_check_dependency(
                       perm_codename='services.delete_service'
                   ))
                   ):
    services_qs = general_filter_queryset(
        qs_or_model=Service,
        curr_site=curr_site,
        curr_user=curr_user,
        perm_codename='services.delete_service'
    )
    srv = get_object_or_404(queryset=services_qs, pk=service_id)

    with transaction.atomic():
        srv.delete()
        curr_user.log(
            do_type=UserProfileLogActionType.DELETE_SERVICE,
            additional_text='"%(title)s", "%(descr)s", %(amount).2f' % {
                "title": srv.title or "-",
                "descr": srv.descr or "-",
                "amount": srv.cost or 0.0
            }
        )


@router.get('/{service_id}/',
            response_model=schemas.ServiceModelSchema,
            response_model_exclude_none=True
            )
def get_service_details(
    service_id: int = Path(gt=0),
    curr_site: Site = Depends(sites_dependency),
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='services.view_service'
    ))
):
    qs = general_filter_queryset(
        qs_or_model=Service.objects.annotate(usercount=Count("link_to_service")),
        curr_site=curr_site,
        curr_user=curr_user,
        perm_codename='services.view_service'
    )
    srv = get_object_or_404(qs, pk=service_id)
    return schemas.ServiceModelSchema.from_orm(srv)


@router.get('/',
            response_model=IListResponse[schemas.ServiceModelSchema],
            response_model_exclude_none=True
            )
@paginate_qs_path_decorator(
    schema=schemas.ServiceModelSchema,
    db_model=Service
)
def get_all_services(request: Request,
                     groups: Optional[int] = None,
                     curr_user: UserProfile = Depends(permission_check_dependency(
                         perm_codename='services.view_service'
                     )),
                     curr_site: Site = Depends(sites_dependency),
                     pagination: Pagination = Depends()
                     ):
    qs = general_filter_queryset(
        qs_or_model=Service.objects.annotate(usercount=Count("link_to_service")),
        curr_site=curr_site,
        curr_user=curr_user,
        perm_codename='services.view_service'
    )
    if groups is not None:
        qs = qs.filter(groups__in=[groups])
    return qs


@router.post('/',
             status_code=status.HTTP_201_CREATED,
             response_model=schemas.ServiceModelSchema)
def create_new_service(
    service_data: schemas.ServiceModelBaseSchema,
    curr_site: Site = Depends(sites_dependency),
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='services.add_service'
    )),
):
    with transaction.atomic():
        new_service = Service.objects.create(
            **service_data.dict()
        )
        new_service.sites.add(curr_site)
        curr_user.log(
            do_type=UserProfileLogActionType.CREATE_SERVICE,
            additional_text='"%(title)s", "%(descr)s", %(amount).2f' % {
                "title": new_service.title or "-",
                "descr": new_service.descr or "-",
                "amount": new_service.cost or 0.0
            }
        )
    return schemas.ServiceModelSchema.from_orm(new_service)
