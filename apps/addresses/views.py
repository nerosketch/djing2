from typing import Optional

from djing2.lib.fastapi.auth import token_auth_dep
from djing2.lib.fastapi.pagination import paginate_qs_path_decorator
from djing2.lib.fastapi.perms import permission_check_dependency
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request, Depends
from starlette import status

from djing2.lib.fastapi.crud import CrudRouter
from djing2.lib.fastapi.types import MAX_LIMIT, IListResponse, Pagination, NOT_FOUND
from django.db.models import Count
from addresses.models import AddressModel, AddressModelTypes
from addresses.fias_socrbase import AddressFIASInfo, AddressFIASLevelType, IAddressFIASType
from addresses import schemas

router = APIRouter(
    prefix='/addrs',
    tags=['address'],
    dependencies=[Depends(token_auth_dep)]
)

_base_addr_queryset = AddressModel.objects.annotate(
    children_count=Count('addressmodel'),
).order_by('title')


class AddrTypeValLabel(BaseModel):
    value: int
    label: str


@router.get('/get_addr_types/', response_model=list[AddrTypeValLabel])
def get_addr_types():
    """Return all possible variants for address model types"""

    model_types = (AddrTypeValLabel(
        value=value,
        label=str(label)
    ) for value, label in AddressModelTypes.choices)
    return model_types


@router.get('/{addr_id}/get_address_by_type/', response_model=Optional[schemas.AddressModelSchema])
def get_address_by_type(addr_id: int, addr_type: AddressModelTypes) -> Optional[schemas.AddressModelSchema]:
    """
    **Get parent address by type.**

    For example, we have house number with id 194, and we need to get its street.

    Then we can _get_address_by_type(194, AddressModelTypes.STREET)_
    """

    addr = AddressModel.objects.get_address_by_type(
        addr_id=addr_id,
        addr_type=addr_type
    ).first()
    if not addr:
        return None
    return schemas.AddressModelSchema.from_orm(addr)


@router.get('/get_ao_levels/')
def get_ao_levels():
    return ({
        'name': name,
        'value': val
    } for val, name in AddressFIASInfo.get_levels())


@router.get('/{addr_id}/get_id_hierarchy/')
def get_id_hierarchy(addr_id: int):
    ids_tree_query = AddressModel.objects.get_address_recursive_ids(
        addr_id=addr_id,
        direction_down=False
    )
    ids_hierarchy = (addr.pk for addr in AddressModel.objects.filter(pk__in=ids_tree_query))
    return ids_hierarchy


@router.get('/{addr_id}/get_full_title/')
def get_full_title(addr_id: int):
    full_title = AddressModel.objects.get_address_full_title(
        addr_id=addr_id
    )
    return full_title


@router.get('/filter_by_fias_level/', response_model=list[schemas.AddressModelSchema])
def filter_by_fias_level(level: AddressFIASLevelType):
    if level and level > 0:
        qs = AddressModel.objects.filter_by_fias_level(level=level).order_by('title')
        return [schemas.AddressModelSchema.from_orm(a) for a in qs.iterator()]

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Item not found"
    )


@router.get('/get_ao_types/', response_model=list[IAddressFIASType])
def get_ao_types(level: AddressFIASLevelType):
    """Get all address object types."""
    return list(AddressFIASInfo.get_address_types_by_level(level=level))


@router.get('/{addr_id}/get_parent/', response_model=Optional[schemas.AddressModelSchema])
def get_parent(addr_id: int) -> Optional[schemas.AddressModelSchema]:
    try:
        obj = AddressModel.objects.filter(pk=addr_id).select_related('parent_addr').get()
        parent = obj.parent_addr
        if parent:
            return schemas.AddressModelSchema.from_orm(parent)
    except AddressModel.DoesNotExist:
        raise NOT_FOUND


@router.get('/get_all_children/', response_model=list[schemas.AddressModelSchema])
def get_all_children(addr_type: AddressModelTypes, parent_addr_id: Optional[int] = None,
                     parent_type: Optional[AddressModelTypes] = None):
    qs = AddressModel.objects.filter_from_parent(
        addr_type,
        parent_id=parent_addr_id,
        parent_type=parent_type
    ).order_by('title')[:MAX_LIMIT]
    return (schemas.AddressModelSchema.from_orm(a) for a in qs.iterator())


@router.get('/', response_model=IListResponse[schemas.AddressModelSchema], dependencies=[Depends(
    permission_check_dependency(perm_codename='addresses.view_addressmodel')
)])
@paginate_qs_path_decorator(schema=schemas.AddressModelSchema, db_model=AddressModel)
def get_all_addresses(
    request: Request,
    address_type: Optional[AddressModelTypes] = None,
    parent_addr_id: Optional[int] = None,
    pagination: Pagination = Depends()
):
    qs = _base_addr_queryset

    if parent_addr_id is not None:
        if parent_addr_id > 0:
            qs = qs.filter(parent_addr_id=parent_addr_id)
        else:
            return qs.filter(parent_addr=None)

    if address_type is not None:
        qs = qs.filter(address_type=address_type.value)

    return qs


router.include_router(CrudRouter(
    schema=schemas.AddressModelSchema,
    create_schema=schemas.AddressBaseSchema,
    queryset=_base_addr_queryset,
    get_all_route=False
))
