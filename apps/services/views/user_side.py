from django.contrib.sites.models import Site
from djing2.lib.fastapi.auth import is_customer_auth_dependency
from djing2.lib.fastapi.sites_depend import sites_dependency
from profiles.models import BaseAccount
from services.models import Service
from fastapi import APIRouter, Depends
from services import schemas


router = APIRouter(
    prefix='/user',
    dependencies=[Depends(is_customer_auth_dependency)],
)


@router.get('/',
            response_model=list[schemas.ServiceModelSchema],
            response_model_exclude={'usercount', 'planned_deadline', 'calc_type_name', 'calc_type'}
            )
def get_all_customer_service(
    current_user: BaseAccount = Depends(is_customer_auth_dependency),
    curr_site: Site = Depends(sites_dependency),
):
    user_group = getattr(current_user, 'group', None)
    if not user_group:
        return Service.objects.none()
    qs = Service.objects.filter(
        is_admin=False,
        groups__in=[user_group],
        sites__in=[curr_site]
    )
    return (schemas.ServiceModelSchema.from_orm(s) for s in qs)
