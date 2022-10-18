from typing import Union, Type

from django.shortcuts import _get_queryset
from django.utils.translation import gettext
from django.db.models import QuerySet, Model
from guardian.shortcuts import get_objects_for_user
from fastapi import Depends, HTTPException
from profiles.models import BaseAccount
from starlette import status
from .auth import is_admin_auth_dependency


PERMISSION_DENIED = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail=gettext('Permission denied, check your rights.')
)


def check_perm(user: BaseAccount, perm_codename: str, raise_exception=True) -> bool:
    if user.is_superuser:
        return True
    has_perm = user.has_perm(perm=perm_codename)
    if raise_exception and not has_perm:
        raise PERMISSION_DENIED
    return has_perm


def permission_check_dependency(perm_codename: str):
    def _permission_check_dep(is_auth=Depends(is_admin_auth_dependency)) -> BaseAccount:
        user, token = is_auth
        check_perm(user, perm_codename)
        return user

    return _permission_check_dep


def filter_qs_by_rights(qs_or_model: Union[QuerySet, Type[Model]], curr_user: BaseAccount, perm_codename: str):
    if curr_user.is_superuser:
        return _get_queryset(qs_or_model)
    rqs = get_objects_for_user(
        user=curr_user,
        perms=perm_codename,
        klass=qs_or_model
    )
    return rqs
