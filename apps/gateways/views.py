from django.contrib.sites.models import Site
from django.db.models import Count, Q
from django.db import transaction
from djing2.lib.fastapi.auth import is_admin_auth_dependency
from djing2.lib.fastapi.general_filter import general_filter_queryset
from djing2.lib.fastapi.pagination import paginate_qs_path_decorator
from djing2.lib.fastapi.perms import permission_check_dependency
from djing2.lib.fastapi.sites_depend import sites_dependency
from djing2.lib.fastapi.types import Pagination, NOT_FOUND
from starlette import status
from gateways.models import Gateway, GatewayClassChoices
from profiles.models import UserProfileLogActionType, BaseAccount, UserProfile
from fastapi import APIRouter, Depends, Request, Path
from gateways import schemas


router = APIRouter(
    prefix='/gateways',
    tags=['Gateways'],
    dependencies=[Depends(is_admin_auth_dependency)],
)


@router.patch('/{gw_id}/',
              response_model=schemas.GatewayModelSchema)
def update_gateway(payload: schemas.GatewayWriteOnlySchema,
                   gw_id: int = Path(gt=0, title='Gateway id'),
                   curr_site: Site = Depends(sites_dependency),
                   curr_user: UserProfile = Depends(permission_check_dependency(
                       perm_codename='gateways.change_gateway'
                   )),
                   ):
    gws_qs = general_filter_queryset(
        qs_or_model=Gateway,
        curr_site=curr_site,
        curr_user=curr_user,
        perm_codename='gateways.change_gateway'
    ).filter(pk=gw_id)
    if not gws_qs.exists():
        raise NOT_FOUND
    gws_qs.update(
        **payload.dict(
            exclude_defaults=True,
            exclude_unset=True
        )
    )
    return schemas.GatewayModelSchema.from_orm(gws_qs.first())


@router.delete('/{gw_id}/', response_model=None)
def delete_gateway(gw_id: int = Path(gt=0, title='Gateway'),
                   curr_site: Site = Depends(sites_dependency),
                   curr_user: UserProfile = Depends(permission_check_dependency(
                       perm_codename='gateways.delete_gateway'
                   )),
                   ):
    gws_qs = general_filter_queryset(
        qs_or_model=Gateway,
        curr_site=curr_site,
        curr_user=curr_user,
        perm_codename='gateways.change_gateway'
    ).filter(pk=gw_id)
    if not gws_qs.exists():
        raise NOT_FOUND

    instance = gws_qs.first()
    with transaction.atomic():
        gws_qs.delete()
        curr_user.log(
            do_type=UserProfileLogActionType.DELETE_NAS,
            additional_text='"%(title)s", %(ip)s, %(type)s' % {
                "title": instance.title,
                "ip": instance.ip_address,
                "type": instance.get_gw_type_display()
            }
        )


@router.get('/')
@paginate_qs_path_decorator(
    schema=schemas.GatewayModelSchema,
    db_model=Gateway
)
def get_all_gateways(request: Request,
                     curr_site: Site = Depends(sites_dependency),
                     curr_user: BaseAccount = Depends(permission_check_dependency(
                         perm_codename='gateways.view_gateway'
                     )),
                     pagination: Pagination = Depends(),
                     ):
    queryset = Gateway.objects.annotate(
        customer_count=Count("customer"),
        customer_count_active=Count("customer", filter=Q(customer__is_active=True)),
        customer_count_w_service=Count(
            "customer", filter=Q(customer__is_active=True) & ~Q(customer__current_service=None)
        ),
    )
    queryset = general_filter_queryset(
        qs_or_model=queryset,
        curr_user=curr_user,
        curr_site=curr_site,
        perm_codename='gateways.view_gateway'
    )
    return queryset


@router.post('/',
             response_model=schemas.GatewayModelSchema,
             status_code=status.HTTP_201_CREATED)
def create_gateway(
    payload: schemas.GatewayWriteOnlySchema,
    curr_site: Site = Depends(sites_dependency),
    curr_user: UserProfile = Depends(permission_check_dependency(
        perm_codename='gateways.add_gateway'
    )),
):
    with transaction.atomic():
        new_gw = Gateway.objects.create(payload.json(
            exclude_defaults=True,
            exclude_unset=True
        ))
        new_gw.sites.add(curr_site)
        # log about creating new Gateway
        curr_user.log(
            do_type=UserProfileLogActionType.CREATE_NAS,
            additional_text='"%(title)s", %(ip)s, %(type)s' % {
                "title": new_gw.title,
                "ip": new_gw.ip_address,
                "type": new_gw.get_gw_type_display()
            }
        )
    return schemas.GatewayModelSchema.from_orm(new_gw)


@router.get('/gateway_class_choices/',
            response_model=list[schemas.GwClassChoice])
def gateway_class_choices():
    gwchoices = (schemas.GwClassChoice(v=k, t=v) for k, v in GatewayClassChoices.choices)
    return gwchoices
