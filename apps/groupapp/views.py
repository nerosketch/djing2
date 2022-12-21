from django.contrib.sites.models import Site
from django.db import transaction
from djing2.lib.fastapi.auth import is_admin_auth_dependency
from djing2.lib.fastapi.crud import CrudRouter
from djing2.lib.fastapi.general_filter import general_filter_queryset
from djing2.lib.fastapi.pagination import paginate_qs_path_decorator
from djing2.lib.fastapi.perms import permission_check_dependency
from djing2.lib.fastapi.sites_depend import sites_dependency
from djing2.lib.fastapi.types import IListResponse, Pagination
from profiles.models import BaseAccount
from groupapp.models import Group
from fastapi import APIRouter, Depends, Request
from starlette import status
from groupapp import schemas


router = APIRouter(
    prefix='/groups',
    tags=['Groups'],
    dependencies=[Depends(is_admin_auth_dependency)]
)


router.include_router(CrudRouter(
    schema=schemas.GroupsModelSchema,
    create_schema=schemas.GroupBaseSchema,
    queryset=Group.objects.all(),
    create_route=False,
    get_all_route=False,
    get_one_route=False,
))


@router.get('/',
            response_model=IListResponse[schemas.GroupsModelSchema],
            response_model_exclude_none=True
            )
@paginate_qs_path_decorator(
    schema=schemas.GroupsModelSchema,
    db_model=Group
)
def get_all_groups(request: Request,
                   curr_user: BaseAccount = Depends(permission_check_dependency(
                       perm_codename='groupapp.view_group'
                   )),
                   curr_site: Site = Depends(sites_dependency),
                   pagination: Pagination = Depends()
                   ):
    qs = general_filter_queryset(
        qs_or_model=Group.objects.order_by('title'),
        curr_site=curr_site,
        curr_user=curr_user,
        perm_codename='groupapp.view_group'
    )
    return qs


@router.post('/',
             status_code=status.HTTP_201_CREATED,
             response_model=schemas.GroupsModelSchema,
             dependencies=[Depends(permission_check_dependency(
                 perm_codename='groupapp.add_group'
             ))]
             )
def create_new_group(
    group_data: schemas.GroupBaseSchema,
    curr_site: Site = Depends(sites_dependency),
):
    with transaction.atomic():
        new_group = Group.objects.create(
            **group_data.dict()
        )
        new_group.sites.add(curr_site)
    return schemas.GroupsModelSchema.from_orm(new_group)
